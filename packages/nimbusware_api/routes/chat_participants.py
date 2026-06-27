from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from nimbusware_api.deps import ChatStoreDep, CollabStoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep, OptionalUserDep
from nimbusware_api.routes.chat_collab_common import actor_user_id, require_collab_enabled
from nimbusware_api.routes.chat_common import session_or_404 as _session_or_404
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
) -> str | None:
    for candidate in (body_discipline, invite_discipline):
        normalized = _normalize_discipline_or_none(candidate)
        if normalized:
            return normalized
    profile = load_user_discipline_profile(str(user_id))
    return profile.get("default_discipline")


@router.get("/join-preview", response_model=JoinPreviewResponse)
def preview_chat_join(
    token: str,
    collab_store: CollabStoreDep,
) -> JoinPreviewResponse:
    _require_collab()
    invite = collab_store.peek_invite(token.strip())
    if invite is None:
        raise HTTPException(
            status_code=404,
            detail=problem("invite_invalid", "invite token invalid or expired"),
        )
    return JoinPreviewResponse(
        role=invite.role,
        recommended_discipline=invite.recommended_discipline,
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
    _session_or_404(chat_store, session_id)
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
    _session_or_404(chat_store, session_id)
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
    _session_or_404(chat_store, session_id)
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
    _session_or_404(chat_store, session_id)
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
    session = _session_or_404(chat_store, invite.session_id)
    discipline = _resolve_join_discipline(
        body_discipline=body.user_discipline,
        invite_discipline=invite.recommended_discipline,
        user_id=user.user_id,
    )
    collab_store.add_participant(
        session_id=invite.session_id,
        user_id=user.user_id,
        role=invite.role,
        user_discipline=discipline,
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
    _session_or_404(chat_store, session_id)
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
