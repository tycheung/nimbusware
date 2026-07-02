from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from nimbusware_api.deps import ChatStoreDep, CollabStoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep, OptionalUserDep
from nimbusware_api.routes.chat_common import actor_user_id, require_collab_enabled, session_or_404
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_auth.models import SESSION_PARTICIPANT_ROLES
from nimbusware_auth.permissions import require_session_participant
from nimbusware_maker.collab_disciplines import normalize_discipline
from nimbusware_maker.user_discipline_profile import load_user_discipline_profile

router = APIRouter(prefix="/chat", tags=["maker"])


class ParticipantBody(BaseModel):
    user_id: str = Field(min_length=36, max_length=36)
    role: str = Field(default="session_read", max_length=32)
    user_discipline: str | None = Field(default=None, max_length=32)


class InviteBody(BaseModel):
    role: str = Field(default="session_read", max_length=32)
    expires_hours: int = Field(default=24, ge=1, le=168)
    recommended_discipline: str | None = Field(default=None, max_length=32)


class JoinBody(BaseModel):
    token: str = Field(min_length=8, max_length=256)
    user_discipline: str | None = Field(default=None, max_length=32)


class ParticipantDisciplineBody(BaseModel):
    user_discipline: str | None = Field(default=None, max_length=32)


class ParticipantResponse(BaseModel):
    session_id: str
    user_id: str
    role: str
    joined_at: str
    username: str | None = None
    display_name: str | None = None
    user_discipline: str | None = None


class InviteResponse(BaseModel):
    invite_id: str
    session_id: str
    role: str
    join_url: str
    expires_at: str
    recommended_discipline: str | None = None


class JoinPreviewResponse(BaseModel):
    role: str
    recommended_discipline: str | None = None
    suggested_agent_overlay: str | None = None


class JoinResponse(BaseModel):
    session_id: str
    project_id: str
    role: str


def _participant_response(row: Any) -> ParticipantResponse:
    d = row.to_dict()
    return ParticipantResponse(**d)


def _normalize_discipline_or_none(raw: str | None) -> str | None:
    if raw is None or not str(raw).strip():
        return None
    return normalize_discipline(str(raw))


def _resolve_join_discipline(
    *,
    body_discipline: str | None,
    invite_discipline: str | None,
    user_id: UUID,
    tenant_slug: str | None = None,
) -> str | None:
    for candidate in (body_discipline, invite_discipline):
        normalized = _normalize_discipline_or_none(candidate)
        if normalized:
            return normalized
    from nimbusware_maker.tenant_collab_defaults import tenant_default_join_discipline

    tenant_hat = tenant_default_join_discipline(tenant_slug)
    if tenant_hat:
        return tenant_hat
    profile = load_user_discipline_profile(str(user_id))
    return profile.get("default_discipline")


def _tenant_slug_for_session(session: Any) -> str | None:
    tenant_id = getattr(session, "tenant_id", None)
    if tenant_id is None:
        return None
    try:
        from nimbusware_env.env_flags import nimbusware_database_url
        from nimbusware_iam.store import build_iam_store

        iam = build_iam_store(nimbusware_database_url())
        tenant = iam.get_tenant(UUID(str(tenant_id)))
        if tenant is not None:
            return str(getattr(tenant, "slug", "") or "").strip() or None
    except Exception:
        return None
    return None


@router.get("/join-preview", response_model=JoinPreviewResponse)
def preview_chat_join(
    token: str,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
) -> JoinPreviewResponse:
    _require_collab()
    invite = collab_store.peek_invite(token.strip())
    if invite is None:
        raise HTTPException(
            status_code=404,
            detail=problem("invite_invalid", "invite token invalid or expired"),
        )
    discipline = _normalize_discipline_or_none(invite.recommended_discipline)
    tenant_slug = None
    try:
        session = chat_store.get_session(invite.session_id)
        if session is not None:
            tenant_slug = _tenant_slug_for_session(session)
            if not discipline:
                from nimbusware_maker.tenant_collab_defaults import tenant_default_join_discipline

                discipline = tenant_default_join_discipline(tenant_slug)
    except Exception:
        pass
    from nimbusware_maker.tenant_collab_defaults import tenant_default_agent_overlay

    overlay = tenant_default_agent_overlay(tenant_slug, discipline)
    return JoinPreviewResponse(
        role=invite.role,
        recommended_discipline=discipline or invite.recommended_discipline,
        suggested_agent_overlay=overlay,
    )


def _require_collab() -> None:
    require_collab_enabled()


def _actor_id(request: Request, user: OptionalUserDep) -> UUID:
    return actor_user_id(request, user)


@router.get(
    "/sessions/{session_id}/participants",
    response_model=list[ParticipantResponse],
    responses={404: PROBLEM_RESPONSE_404},
)
def list_session_participants(
    session_id: UUID,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    request: Request,
    user: OptionalUserDep,
) -> list[ParticipantResponse]:
    _require_collab()
    session_or_404(chat_store, session_id)
    actor = _actor_id(request, user)
    require_session_participant(
        collab_store,
        session_id=session_id,
        user_id=actor,
        minimum_role="session_read",
    )
    rows = collab_store.list_participants(session_id)
    return [_participant_response(r) for r in rows]


@router.post(
    "/sessions/{session_id}/participants",
    response_model=ParticipantResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def add_session_participant(
    session_id: UUID,
    body: ParticipantBody,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    request: Request,
    user: OptionalUserDep,
) -> ParticipantResponse:
    _require_collab()
    session = session_or_404(chat_store, session_id)
    actor = _actor_id(request, user)
    require_session_participant(
        collab_store,
        session_id=session_id,
        user_id=actor,
        minimum_role="session_admin",
    )
    role = body.role.strip().lower()
    if role not in SESSION_PARTICIPANT_ROLES:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "invalid participant role"),
        )
    try:
        target = UUID(body.user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "user_id must be a UUID"),
        ) from exc
    tenant_slug = _tenant_slug_for_session(session)
    from nimbusware_maker.collab_policy_enforcement import (
        CollabPolicyViolation,
        assert_participant_capacity,
    )

    try:
        assert_participant_capacity(
            collab_store,
            session_id,
            tenant_slug=tenant_slug,
            user_id=target,
        )
    except CollabPolicyViolation as exc:
        raise HTTPException(
            status_code=403,
            detail=problem("collab_policy_violation", str(exc)),
        ) from exc
    try:
        row = collab_store.add_participant(
            session_id=session_id,
            user_id=target,
            role=role,
            user_discipline=_normalize_discipline_or_none(body.user_discipline),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    return _participant_response(row)


@router.delete(
    "/sessions/{session_id}/participants/{user_id}",
    responses={404: PROBLEM_RESPONSE_404},
)
def remove_session_participant(
    session_id: UUID,
    user_id: UUID,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    request: Request,
    user: OptionalUserDep,
) -> dict[str, bool]:
    _require_collab()
    session_or_404(chat_store, session_id)
    actor = _actor_id(request, user)
    require_session_participant(
        collab_store,
        session_id=session_id,
        user_id=actor,
        minimum_role="session_admin",
    )
    if not collab_store.remove_participant(session_id, user_id):
        raise HTTPException(
            status_code=404,
            detail=problem("participant_not_found", "participant not found"),
        )
    return {"ok": True}


@router.post(
    "/sessions/{session_id}/invites",
    response_model=InviteResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def create_session_invite(
    session_id: UUID,
    body: InviteBody,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    request: Request,
    user: OptionalUserDep,
) -> InviteResponse:
    _require_collab()
    session_or_404(chat_store, session_id)
    actor = _actor_id(request, user)
    require_session_participant(
        collab_store,
        session_id=session_id,
        user_id=actor,
        minimum_role="session_admin",
    )
    role = body.role.strip().lower()
    if role not in SESSION_PARTICIPANT_ROLES:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "invalid participant role"),
        )
    expires_at = datetime.now(timezone.utc) + timedelta(hours=body.expires_hours)
    invite = collab_store.create_invite(
        session_id=session_id,
        role=role,
        created_by=actor,
        expires_at=expires_at,
        recommended_discipline=_normalize_discipline_or_none(body.recommended_discipline),
    )
    join_url = f"/v1/maker/app/#/chat/join/{invite.token}"
    return InviteResponse(
        invite_id=str(invite.invite_id),
        session_id=str(invite.session_id),
        role=invite.role,
        join_url=join_url,
        expires_at=invite.expires_at.isoformat(),
        recommended_discipline=invite.recommended_discipline,
    )


@router.post("/join", response_model=JoinResponse)
def join_chat_session(
    body: JoinBody,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    user: AuthUserDep,
) -> JoinResponse:
    _require_collab()
    invite = collab_store.consume_invite(body.token.strip())
    if invite is None:
        raise HTTPException(
            status_code=404,
            detail=problem("invite_invalid", "invite token invalid or expired"),
        )
    session = session_or_404(chat_store, invite.session_id)
    tenant_slug = _tenant_slug_for_session(session)
    from nimbusware_maker.collab_policy_enforcement import (
        CollabPolicyViolation,
        assert_link_join_allowed,
        assert_participant_capacity,
    )

    try:
        assert_link_join_allowed(tenant_slug=tenant_slug)
        assert_participant_capacity(
            collab_store,
            invite.session_id,
            tenant_slug=tenant_slug,
            user_id=user.user_id,
        )
    except CollabPolicyViolation as exc:
        raise HTTPException(
            status_code=403,
            detail=problem("collab_policy_violation", str(exc)),
        ) from exc
    discipline = _resolve_join_discipline(
        body_discipline=body.user_discipline,
        invite_discipline=invite.recommended_discipline,
        user_id=user.user_id,
        tenant_slug=tenant_slug,
    )
    collab_store.add_participant(
        session_id=invite.session_id,
        user_id=user.user_id,
        role=invite.role,
        user_discipline=discipline,
    )
    from nimbusware_maker.tenant_collab_defaults import seed_tenant_agent_overlay_on_join

    seed_tenant_agent_overlay_on_join(
        user.user_id,
        discipline,
        tenant_slug=tenant_slug,
    )
    return JoinResponse(
        session_id=str(session.session_id),
        project_id=str(session.project_id),
        role=invite.role,
    )


@router.put(
    "/sessions/{session_id}/participants/me/discipline",
    response_model=ParticipantResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def update_my_session_discipline(
    session_id: UUID,
    body: ParticipantDisciplineBody,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    user: AuthUserDep,
) -> ParticipantResponse:
    _require_collab()
    session_or_404(chat_store, session_id)
    require_session_participant(
        collab_store,
        session_id=session_id,
        user_id=user.user_id,
        minimum_role="session_read",
    )
    discipline = _normalize_discipline_or_none(body.user_discipline)
    row = collab_store.update_participant_discipline(
        session_id=session_id,
        user_id=user.user_id,
        user_discipline=discipline,
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=problem("participant_not_found", "participant not found"),
        )
    return _participant_response(row)
