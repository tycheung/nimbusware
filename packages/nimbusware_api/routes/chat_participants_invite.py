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
from nimbusware_api.routes.chat_participant_support import (
    normalize_discipline_or_none,
    resolve_join_discipline,
    tenant_slug_for_session,
)
from nimbusware_auth.models import SESSION_PARTICIPANT_ROLES

router = APIRouter(prefix="/chat", tags=["maker"])


class InviteBody(BaseModel):
    role: str = Field(default="session_read", max_length=32)
    expires_hours: int = Field(default=24, ge=1, le=168)
    recommended_discipline: str | None = Field(default=None, max_length=32)


class JoinBody(BaseModel):
    token: str = Field(min_length=8, max_length=256)
    user_discipline: str | None = Field(default=None, max_length=32)


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


@router.get("/join-preview", response_model=JoinPreviewResponse)
def preview_chat_join(
    token: str,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
) -> JoinPreviewResponse:
    require_collab_enabled()
    invite = collab_store.peek_invite(token.strip())
    if invite is None:
        raise HTTPException(
            status_code=404,
            detail=problem("invite_invalid", "invite token invalid or expired"),
        )
    discipline = normalize_discipline_or_none(invite.recommended_discipline)
    tenant_slug = None
    try:
        session = chat_store.get_session(invite.session_id)
        if session is not None:
            tenant_slug = tenant_slug_for_session(session)
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


@router.post(
    "/sessions/{session_id}/invites",
    response_model=InviteResponse,
)
def create_session_invite(
    session_id: UUID,
    body: InviteBody,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    request: Request,
    user: OptionalUserDep,
) -> InviteResponse:
    from nimbusware_auth.permissions import require_session_participant

    require_collab_enabled()
    session_or_404(chat_store, session_id)
    actor = actor_user_id(request, user)
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
        recommended_discipline=normalize_discipline_or_none(body.recommended_discipline),
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
    require_collab_enabled()
    invite = collab_store.consume_invite(body.token.strip())
    if invite is None:
        raise HTTPException(
            status_code=404,
            detail=problem("invite_invalid", "invite token invalid or expired"),
        )
    session = session_or_404(chat_store, invite.session_id)
    tenant_slug = tenant_slug_for_session(session)
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
    discipline = resolve_join_discipline(
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
