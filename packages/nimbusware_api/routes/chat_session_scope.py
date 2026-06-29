from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from nimbusware_api.deps import ChatStoreDep, CollabStoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep, OptionalUserDep
from nimbusware_api.routes.chat_collab_common import actor_user_id
from nimbusware_api.routes.chat_common import session_or_404 as _session_or_404
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_auth.permissions import require_session_participant
from nimbusware_env.env_flags import nimbusware_collab_enabled
from nimbusware_maker.session_scope import (
    approve_scope_pending,
    get_scope_pending,
    publish_scope_pending,
)

router = APIRouter(prefix="/chat", tags=["maker"])


def _require_scope_writer(
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    session_id: UUID,
    actor: UUID,
) -> None:
    if nimbusware_collab_enabled():
        participants = collab_store.list_participants(session_id)
        if participants:
            require_session_participant(
                collab_store,
                session_id=session_id,
                user_id=actor,
                minimum_role="session_write",
            )
            return
    session = chat_store.get_session(session_id)
    host = getattr(session, "host_user_id", None) if session else None
    if host is None or host == actor:
        return
    raise HTTPException(
        status_code=403,
        detail=problem("forbidden", "session write access required"),
    )


def _require_scope_reader(
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    session_id: UUID,
    actor: UUID,
) -> None:
    if nimbusware_collab_enabled():
        participants = collab_store.list_participants(session_id)
        if participants:
            require_session_participant(
                collab_store,
                session_id=session_id,
                user_id=actor,
                minimum_role="session_read",
            )
            return
    pending = get_scope_pending(chat_store, session_id)
    if pending is not None:
        return
    raise HTTPException(
        status_code=403,
        detail=problem("forbidden", "scope review access required"),
    )


class ScopePublishBody(BaseModel):
    state: dict[str, Any]


class ScopePendingResponse(BaseModel):
    session_id: str
    scope_pending: dict[str, Any] | None = None
    scope_approved: dict[str, Any] | None = None


@router.post(
    "/sessions/{session_id}/scope/publish",
    response_model=ScopePendingResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def post_session_scope_publish(
    session_id: UUID,
    body: ScopePublishBody,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    request: Request,
    user: OptionalUserDep,
) -> ScopePendingResponse:
    _session_or_404(chat_store, session_id)
    actor = actor_user_id(request, user)
    _require_scope_writer(chat_store, collab_store, session_id, actor)
    try:
        publish_scope_pending(chat_store, session_id, body.state)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=problem("session_not_found", str(exc)),
        ) from exc
    session = chat_store.get_session(session_id)
    meta = dict(session.metadata or {}) if session else {}
    return ScopePendingResponse(
        session_id=str(session_id),
        scope_pending=meta.get("scope_pending")
        if isinstance(meta.get("scope_pending"), dict)
        else None,
        scope_approved=meta.get("scope_approved")
        if isinstance(meta.get("scope_approved"), dict)
        else None,
    )


@router.get(
    "/sessions/{session_id}/scope/pending",
    response_model=ScopePendingResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_session_scope_pending(
    session_id: UUID,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    request: Request,
    user: OptionalUserDep,
) -> ScopePendingResponse:
    _session_or_404(chat_store, session_id)
    actor = actor_user_id(request, user)
    _require_scope_reader(chat_store, collab_store, session_id, actor)
    session = chat_store.get_session(session_id)
    meta = dict(session.metadata or {}) if session else {}
    pending = get_scope_pending(chat_store, session_id)
    approved = meta.get("scope_approved")
    return ScopePendingResponse(
        session_id=str(session_id),
        scope_pending=pending,
        scope_approved=approved if isinstance(approved, dict) else None,
    )


@router.post(
    "/sessions/{session_id}/scope/approve",
    response_model=ScopePendingResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def post_session_scope_approve(
    session_id: UUID,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    user: AuthUserDep,
) -> ScopePendingResponse:
    _session_or_404(chat_store, session_id)
    _require_scope_reader(chat_store, collab_store, session_id, user.user_id)
    try:
        confirmed = approve_scope_pending(
            chat_store,
            session_id,
            actor_user_id=str(user.user_id),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=problem("session_not_found", str(exc)),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("scope_not_pending", str(exc)),
        ) from exc
    return ScopePendingResponse(
        session_id=str(session_id),
        scope_pending=None,
        scope_approved=confirmed,
    )
