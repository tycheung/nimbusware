from __future__ import annotations

from typing import Any
from uuid import UUID

from maker.scope_discovery import scope_confirm


def _meta(session: Any) -> dict[str, Any]:
    raw = getattr(session, "metadata", None)
    return dict(raw) if isinstance(raw, dict) else {}


def publish_scope_pending(
    chat_store: Any, session_id: UUID, scope_state: dict[str, Any]
) -> dict[str, Any]:
    session = chat_store.get_session(session_id)
    if session is None:
        raise KeyError("chat_session_not_found")
    meta = _meta(session)
    meta["scope_pending"] = dict(scope_state)
    chat_store.update_session(session_id, metadata=meta)
    return dict(scope_state)


def get_scope_pending(chat_store: Any, session_id: UUID) -> dict[str, Any] | None:
    session = chat_store.get_session(session_id)
    if session is None:
        raise KeyError("chat_session_not_found")
    pending = _meta(session).get("scope_pending")
    return dict(pending) if isinstance(pending, dict) else None


def approve_scope_pending(
    chat_store: Any,
    session_id: UUID,
    *,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    session = chat_store.get_session(session_id)
    if session is None:
        raise KeyError("chat_session_not_found")
    meta = _meta(session)
    pending = meta.get("scope_pending")
    if not isinstance(pending, dict):
        raise ValueError("no scope pending approval")
    confirmed = scope_confirm(pending)
    meta["scope_approved"] = confirmed
    meta.pop("scope_pending", None)
    if actor_user_id:
        meta["scope_approved_by"] = actor_user_id
    chat_store.update_session(session_id, metadata=meta)
    return confirmed
