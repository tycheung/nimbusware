from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request

from api.access import assert_project_accessible
from api.deps import ChatStoreDep, CollabStoreDep, ProjectStoreDep
from api.errors import problem
from auth.models import UserRecord
from auth.permissions import require_session_participant
from auth.session_cookie import user_id_from_request
from env.env_flags import nimbusware_collab_enabled
from maker.chat.session_models import ChatSessionRecord


def require_collab_enabled() -> None:
    if not nimbusware_collab_enabled():
        raise HTTPException(
            status_code=403,
            detail=problem("collab_disabled", "collaborative chat is disabled"),
        )


def actor_user_id(request: Request, user: UserRecord | None) -> UUID:
    if user is not None:
        return user.user_id
    uid = user_id_from_request(request)
    if uid is not None:
        return uid
    raise HTTPException(
        status_code=401,
        detail=problem("unauthorized", "sign in required"),
    )


def session_or_404(chat_store: ChatStoreDep, session_id: UUID) -> ChatSessionRecord:
    session = chat_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "chat_session_not_found",
                "Unknown chat session",
                details={"session_id": str(session_id)},
            ),
        )
    return session


def chat_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        code = str(exc.args[0]) if exc.args else "not_found"
        if code == "chat_turn_not_found":
            return HTTPException(
                status_code=404,
                detail=problem(code, "Unknown chat turn"),
            )
        return HTTPException(
            status_code=404,
            detail=problem("chat_session_not_found", "Unknown chat session"),
        )
    if isinstance(exc, ValueError):
        return HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        )
    raise exc


def project_metadata(project_store: ProjectStoreDep, project_uuid: UUID) -> dict[str, Any]:
    record = project_store.get(project_uuid)
    if record is None:
        raise HTTPException(
            status_code=422,
            detail=problem("project_not_found", f"Unknown project id: {project_uuid}"),
        )
    assert_project_accessible(record)
    data = record.to_dict()
    return {
        "project_id": data.get("project_id"),
        "name": data.get("name"),
        "template": data.get("template"),
        "default_workflow_profile": data.get("default_workflow_profile"),
        "default_work_type": data.get("default_work_type"),
    }


def collab_session_actor(
    chat_store: ChatStoreDep,
    session_id: UUID,
    request: Request,
    user: UserRecord | None,
) -> tuple[ChatSessionRecord, UUID]:
    session = session_or_404(chat_store, session_id)
    actor = actor_user_id(request, user)
    return session, actor


def require_collab_session_participant(
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    session_id: UUID,
    request: Request,
    user: UserRecord | None,
    *,
    minimum_role: str = "session_read",
) -> tuple[ChatSessionRecord, UUID]:
    require_collab_enabled()
    session, actor = collab_session_actor(chat_store, session_id, request, user)
    require_session_participant(
        collab_store,
        session_id=session_id,
        user_id=actor,
        minimum_role=minimum_role,
    )
    return session, actor
