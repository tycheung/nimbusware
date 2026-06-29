from __future__ import annotations

from uuid import uuid4

import pytest

from nimbusware_maker.session_scope import (
    approve_scope_pending,
    get_scope_pending,
    publish_scope_pending,
)


class _MemChatStore:
    def __init__(self) -> None:
        self._sessions: dict = {}

    def seed(self, session_id, metadata=None):
        from types import SimpleNamespace

        self._sessions[session_id] = SimpleNamespace(
            session_id=session_id,
            metadata=dict(metadata or {}),
        )

    def get_session(self, session_id):
        return self._sessions.get(session_id)

    def update_session(self, session_id, *, metadata=None):
        session = self._sessions[session_id]
        session.metadata = dict(metadata or {})
        return session


def test_publish_and_approve_scope_pending() -> None:
    store = _MemChatStore()
    session_id = uuid4()
    store.seed(session_id)
    state = {
        "discovery_complete": True,
        "stack_manifest": {
            "surfaces": ["web", "api"],
            "stacks": {"web": "react_vite", "api": "fastapi_python"},
        },
    }
    publish_scope_pending(store, session_id, state)
    pending = get_scope_pending(store, session_id)
    assert pending is not None
    assert pending["stack_manifest"]["surfaces"] == ["web", "api"]
    approved = approve_scope_pending(store, session_id, actor_user_id="manager-1")
    assert approved.get("scope_confirmed") is True
    assert get_scope_pending(store, session_id) is None


def test_approve_without_pending_raises() -> None:
    store = _MemChatStore()
    session_id = uuid4()
    store.seed(session_id)
    with pytest.raises(ValueError, match="no scope pending"):
        approve_scope_pending(store, session_id)
