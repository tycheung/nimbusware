from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException

from nimbusware_api.deps import ChatStoreDep
from nimbusware_api.errors import problem
from nimbusware_maker.chat_models import ChatSessionRecord
from nimbusware_maker.quick_mode import quick_mode_enabled


def platform_hints(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    hints = dict(extra or {})
    hints.setdefault("quick_mode", quick_mode_enabled())
    return hints


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
