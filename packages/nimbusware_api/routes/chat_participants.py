from __future__ import annotations

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
    tenant_slug_for_session,
)
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_auth.models import SESSION_PARTICIPANT_ROLES
from nimbusware_auth.permissions import require_session_participant

router = APIRouter(prefix="/chat", tags=["maker"])


class ParticipantBody(BaseModel):
    user_id: str = Field(min_length=36, max_length=36)
    role: str = Field(default="session_read", max_length=32)
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


def _participant_response(row: Any) -> ParticipantResponse:
    d = row.to_dict()
    return ParticipantResponse(**d)


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
    require_collab_enabled()
    session_or_404(chat_store, session_id)
    actor = actor_user_id(request, user)
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
    require_collab_enabled()
    session = session_or_404(chat_store, session_id)
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
    try:
        target = UUID(body.user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "user_id must be a UUID"),
        ) from exc
    tenant_slug = tenant_slug_for_session(session)
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
            user_discipline=normalize_discipline_or_none(body.user_discipline),
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
    require_collab_enabled()
    session_or_404(chat_store, session_id)
    actor = actor_user_id(request, user)
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
    require_collab_enabled()
    session_or_404(chat_store, session_id)
    require_session_participant(
        collab_store,
        session_id=session_id,
        user_id=user.user_id,
        minimum_role="session_read",
    )
    discipline = normalize_discipline_or_none(body.user_discipline)
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
