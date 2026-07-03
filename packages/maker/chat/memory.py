from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

from iam.constants import DEFAULT_TENANT_ID
from maker.chat.analytics import _in_memory_analytics_rows
from maker.chat.graph import (
    _validate_role,
    build_graph,
    path_to_root,
)
from maker.chat.rows import _UNSET, _utc_now
from maker.chat.session_models import ChatSessionRecord, ChatTurnRecord


class InMemoryChatStore:
    def __init__(self) -> None:
        self._sessions: dict[UUID, ChatSessionRecord] = {}
        self._turns: dict[UUID, dict[UUID, ChatTurnRecord]] = defaultdict(dict)
        self._ordinal: dict[UUID, int] = defaultdict(int)

    def create_session(
        self,
        *,
        project_id: UUID,
        tenant_id: UUID | None = None,
        host_user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChatSessionRecord:
        now = _utc_now()
        sid = uuid4()
        row = ChatSessionRecord(
            session_id=sid,
            project_id=project_id,
            tenant_id=tenant_id or DEFAULT_TENANT_ID,
            created_at=now,
            updated_at=now,
            host_user_id=host_user_id,
            metadata=dict(metadata or {}),
        )
        self._sessions[sid] = row
        return row

    def get_session(self, session_id: UUID) -> ChatSessionRecord | None:
        return self._sessions.get(session_id)

    def list_sessions(self, *, project_id: UUID) -> list[ChatSessionRecord]:
        rows = [s for s in self._sessions.values() if s.project_id == project_id]
        return sorted(rows, key=lambda s: s.updated_at, reverse=True)

    def find_session_by_run_id(self, run_id: UUID) -> ChatSessionRecord | None:
        for session in self._sessions.values():
            if session.run_id == run_id:
                return session
        return None

    def _turns_for(self, session_id: UUID) -> dict[UUID, ChatTurnRecord]:
        return self._turns[session_id]

    def append_turn(
        self,
        session_id: UUID,
        *,
        role: str,
        text: str,
        payload: dict[str, Any] | None = None,
        parent_turn_id: UUID | None = None,
        work_type: str | None = None,
        work_type_source: str | None = None,
        run_id: UUID | None = None,
        campaign_id: UUID | None = None,
        event_seq: int | None = None,
    ) -> ChatTurnRecord:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError("chat_session_not_found")
        role_n = _validate_role(role)
        turns = self._turns_for(session_id)
        parent = parent_turn_id
        if parent is None:
            parent = session.active_leaf_turn_id
        self._ordinal[session_id] += 1
        turn_id = uuid4()
        now = _utc_now()
        turn = ChatTurnRecord(
            turn_id=turn_id,
            session_id=session_id,
            parent_turn_id=parent,
            ordinal=self._ordinal[session_id],
            role=role_n,
            text=text,
            payload=dict(payload or {}),
            work_type=work_type,
            work_type_source=work_type_source,
            run_id=run_id,
            campaign_id=campaign_id,
            event_seq=event_seq,
            posted_at=now,
        )
        turns[turn_id] = turn
        root = session.root_turn_id or turn_id
        title = session.title
        if title is None and role_n == "user" and text.strip():
            title = text.strip()[:120]
        updated = replace(
            session,
            updated_at=now,
            title=title,
            root_turn_id=root,
            active_leaf_turn_id=turn_id,
            run_id=run_id or session.run_id,
            campaign_id=campaign_id or session.campaign_id,
        )
        self._sessions[session_id] = updated
        return turn

    def fork_at_turn(self, session_id: UUID, turn_id: UUID) -> ChatSessionRecord:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError("chat_session_not_found")
        turns = self._turns_for(session_id)
        if turn_id not in turns:
            raise KeyError("chat_turn_not_found")
        now = _utc_now()
        updated = replace(session, updated_at=now, active_leaf_turn_id=turn_id)
        self._sessions[session_id] = updated
        return updated

    def set_active_leaf(self, session_id: UUID, leaf_turn_id: UUID) -> ChatSessionRecord:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError("chat_session_not_found")
        turns = self._turns_for(session_id)
        if leaf_turn_id not in turns:
            raise KeyError("chat_turn_not_found")
        children_map: dict[UUID, list[UUID]] = defaultdict(list)
        for t in turns.values():
            if t.parent_turn_id is not None:
                children_map[t.parent_turn_id].append(t.turn_id)
        if children_map.get(leaf_turn_id):
            raise ValueError("active_leaf_must_be_a_branch_tip")
        now = _utc_now()
        updated = replace(session, updated_at=now, active_leaf_turn_id=leaf_turn_id)
        self._sessions[session_id] = updated
        return updated

    def update_session(
        self,
        session_id: UUID,
        *,
        last_classification: dict[str, Any] | None = None,
        work_type_override: str | None = None,
        run_id: UUID | None = None,
        campaign_id: UUID | None = None,
        host_user_id: UUID | None = None,
        workload_distribution: str | None = None,
        folder_id: UUID | None | Any = _UNSET,
        tags: list[str] | None | Any = _UNSET,
        metadata: dict[str, Any] | None = None,
    ) -> ChatSessionRecord:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError("chat_session_not_found")
        now = _utc_now()
        overrides: dict[str, Any] = {"updated_at": now}
        if last_classification is not None:
            overrides["last_classification"] = last_classification
        if work_type_override is not None:
            overrides["work_type_override"] = work_type_override
        if run_id is not None:
            overrides["run_id"] = run_id
        if campaign_id is not None:
            overrides["campaign_id"] = campaign_id
        if host_user_id is not None:
            overrides["host_user_id"] = host_user_id
        if workload_distribution is not None:
            overrides["workload_distribution"] = workload_distribution
        if folder_id is not _UNSET:
            overrides["folder_id"] = folder_id
        if tags is not _UNSET:
            overrides["tags"] = tuple(tags or [])
        if metadata is not None:
            overrides["metadata"] = dict(metadata)
        updated = replace(session, **overrides)
        self._sessions[session_id] = updated
        return updated

    def get_active_path(self, session_id: UUID) -> list[ChatTurnRecord]:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError("chat_session_not_found")
        if session.active_leaf_turn_id is None:
            return []
        return path_to_root(self._turns_for(session_id), session.active_leaf_turn_id)

    def get_graph(self, session_id: UUID) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError("chat_session_not_found")
        return build_graph(session, self._turns_for(session_id))

    def list_turns(self, session_id: UUID) -> list[ChatTurnRecord]:
        turns = self._turns_for(session_id)
        return sorted(turns.values(), key=lambda t: t.ordinal)

    def list_recent_analytics_turn_rows(
        self,
        *,
        limit_sessions: int = 500,
    ) -> list[dict[str, Any]]:
        return _in_memory_analytics_rows(self, limit_sessions=limit_sessions)
