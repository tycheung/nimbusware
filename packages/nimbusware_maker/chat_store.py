from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from nimbusware_iam.constants import DEFAULT_TENANT_ID
from nimbusware_maker.chat_models import CHAT_TURN_ROLES, ChatSessionRecord, ChatTurnRecord


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_role(role: str) -> str:
    r = role.strip().lower()
    if r not in CHAT_TURN_ROLES:
        msg = f"invalid chat turn role: {role!r}"
        raise ValueError(msg)
    return r


def path_to_root(turns: dict[UUID, ChatTurnRecord], leaf_id: UUID) -> list[ChatTurnRecord]:
    path: list[ChatTurnRecord] = []
    cur: UUID | None = leaf_id
    seen: set[UUID] = set()
    while cur is not None:
        if cur in seen:
            break
        seen.add(cur)
        turn = turns.get(cur)
        if turn is None:
            break
        path.append(turn)
        cur = turn.parent_turn_id
    path.reverse()
    return path


def child_turn_ids(turns: dict[UUID, ChatTurnRecord], parent_id: UUID) -> list[UUID]:
    kids = [t.turn_id for t in turns.values() if t.parent_turn_id == parent_id]
    return sorted(kids, key=lambda tid: turns[tid].ordinal)


def sibling_count(turns: dict[UUID, ChatTurnRecord], turn_id: UUID) -> int:
    turn = turns.get(turn_id)
    if turn is None or turn.parent_turn_id is None:
        return 0
    return len(child_turn_ids(turns, turn.parent_turn_id))


def leaf_descendants(turns: dict[UUID, ChatTurnRecord], ancestor_id: UUID) -> list[UUID]:
    children_map: dict[UUID, list[UUID]] = defaultdict(list)
    for t in turns.values():
        if t.parent_turn_id is not None:
            children_map[t.parent_turn_id].append(t.turn_id)

    def is_ancestor_of(leaf: UUID, ancestor: UUID) -> bool:
        cur: UUID | None = leaf
        seen: set[UUID] = set()
        while cur is not None:
            if cur == ancestor:
                return True
            if cur in seen:
                return False
            seen.add(cur)
            node = turns.get(cur)
            if node is None:
                return False
            cur = node.parent_turn_id
        return False

    leaves = [tid for tid in turns if not children_map.get(tid)]
    return [lid for lid in leaves if is_ancestor_of(lid, ancestor_id)]


def build_graph(session: ChatSessionRecord, turns: dict[UUID, ChatTurnRecord]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for turn in sorted(turns.values(), key=lambda t: t.ordinal):
        siblings = sibling_count(turns, turn.turn_id)
        node = turn.to_dict()
        node["child_count"] = len(child_turn_ids(turns, turn.turn_id))
        node["sibling_count"] = siblings
        node["is_active_path"] = False
        nodes.append(node)
        if turn.parent_turn_id is not None:
            edges.append(
                {
                    "from_turn_id": str(turn.parent_turn_id),
                    "to_turn_id": str(turn.turn_id),
                }
            )
    if session.active_leaf_turn_id:
        active_ids = {str(t.turn_id) for t in path_to_root(turns, session.active_leaf_turn_id)}
        for node in nodes:
            if node["turn_id"] in active_ids:
                node["is_active_path"] = True
    branches: list[dict[str, Any]] = []
    for turn in turns.values():
        if turn.parent_turn_id is None:
            continue
        sibs = child_turn_ids(turns, turn.parent_turn_id)
        if len(sibs) > 1:
            branches.append(
                {
                    "parent_turn_id": str(turn.parent_turn_id),
                    "child_turn_ids": [str(x) for x in sibs],
                }
            )
    return {
        "session_id": str(session.session_id),
        "active_leaf_turn_id": (
            str(session.active_leaf_turn_id) if session.active_leaf_turn_id else None
        ),
        "nodes": nodes,
        "edges": edges,
        "branches": branches,
    }


def turns_to_legacy_messages(turns: list[ChatTurnRecord]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for turn in turns:
        if turn.role == "user":
            out.append(
                {
                    "role": "user",
                    "text": turn.text,
                    "attachments": turn.payload.get("attachments") or [],
                    "posted_at": turn.posted_at.isoformat() if turn.posted_at else None,
                    "turn_id": str(turn.turn_id),
                }
            )
        elif turn.role in {"system", "classifier", "work_type_switch", "run_status", "theater"}:
            out.append(
                {
                    "role": "system",
                    "text": turn.text,
                    "turn_id": str(turn.turn_id),
                    "kind": turn.role,
                    "posted_at": turn.posted_at.isoformat() if turn.posted_at else None,
                }
            )
    return out


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
    ) -> ChatSessionRecord:
        now = _utc_now()
        sid = uuid4()
        row = ChatSessionRecord(
            session_id=sid,
            project_id=project_id,
            tenant_id=tenant_id or DEFAULT_TENANT_ID,
            created_at=now,
            updated_at=now,
        )
        self._sessions[sid] = row
        return row

    def get_session(self, session_id: UUID) -> ChatSessionRecord | None:
        return self._sessions.get(session_id)

    def list_sessions(self, *, project_id: UUID) -> list[ChatSessionRecord]:
        rows = [s for s in self._sessions.values() if s.project_id == project_id]
        return sorted(rows, key=lambda s: s.updated_at, reverse=True)

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
        updated = ChatSessionRecord(
            session_id=session.session_id,
            project_id=session.project_id,
            tenant_id=session.tenant_id,
            created_at=session.created_at,
            updated_at=now,
            title=title,
            root_turn_id=root,
            active_leaf_turn_id=turn_id,
            last_classification=session.last_classification,
            work_type_override=session.work_type_override,
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
        updated = ChatSessionRecord(
            session_id=session.session_id,
            project_id=session.project_id,
            tenant_id=session.tenant_id,
            created_at=session.created_at,
            updated_at=now,
            title=session.title,
            root_turn_id=session.root_turn_id,
            active_leaf_turn_id=turn_id,
            last_classification=session.last_classification,
            work_type_override=session.work_type_override,
            run_id=session.run_id,
            campaign_id=session.campaign_id,
        )
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
        updated = ChatSessionRecord(
            session_id=session.session_id,
            project_id=session.project_id,
            tenant_id=session.tenant_id,
            created_at=session.created_at,
            updated_at=now,
            title=session.title,
            root_turn_id=session.root_turn_id,
            active_leaf_turn_id=leaf_turn_id,
            last_classification=session.last_classification,
            work_type_override=session.work_type_override,
            run_id=session.run_id,
            campaign_id=session.campaign_id,
        )
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
    ) -> ChatSessionRecord:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError("chat_session_not_found")
        now = _utc_now()
        updated = ChatSessionRecord(
            session_id=session.session_id,
            project_id=session.project_id,
            tenant_id=session.tenant_id,
            created_at=session.created_at,
            updated_at=now,
            title=session.title,
            root_turn_id=session.root_turn_id,
            active_leaf_turn_id=session.active_leaf_turn_id,
            last_classification=(
                last_classification
                if last_classification is not None
                else session.last_classification
            ),
            work_type_override=(
                work_type_override if work_type_override is not None else session.work_type_override
            ),
            run_id=run_id if run_id is not None else session.run_id,
            campaign_id=campaign_id if campaign_id is not None else session.campaign_id,
        )
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


def _session_from_row(row: dict[str, object]) -> ChatSessionRecord:
    return ChatSessionRecord(
        session_id=row["session_id"],  # type: ignore[arg-type]
        project_id=row["project_id"],  # type: ignore[arg-type]
        tenant_id=row["tenant_id"],  # type: ignore[arg-type]
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
        title=str(row["title"]) if row.get("title") else None,
        root_turn_id=row.get("root_turn_id"),  # type: ignore[arg-type]
        active_leaf_turn_id=row.get("active_leaf_turn_id"),  # type: ignore[arg-type]
        last_classification=row.get("last_classification"),  # type: ignore[arg-type]
        work_type_override=(
            str(row["work_type_override"]) if row.get("work_type_override") else None
        ),
        run_id=row.get("run_id"),  # type: ignore[arg-type]
        campaign_id=row.get("campaign_id"),  # type: ignore[arg-type]
    )


def _turn_from_row(row: dict[str, object]) -> ChatTurnRecord:
    raw_seq = row.get("event_seq")
    event_seq = int(str(raw_seq)) if raw_seq is not None else None
    return ChatTurnRecord(
        turn_id=row["turn_id"],  # type: ignore[arg-type]
        session_id=row["session_id"],  # type: ignore[arg-type]
        parent_turn_id=row.get("parent_turn_id"),  # type: ignore[arg-type]
        ordinal=int(str(row["ordinal"])),
        role=str(row["role"]),
        text=str(row["text"]),
        payload=row["payload"],  # type: ignore[arg-type]
        work_type=str(row["work_type"]) if row.get("work_type") else None,
        work_type_source=(str(row["work_type_source"]) if row.get("work_type_source") else None),
        run_id=row.get("run_id"),  # type: ignore[arg-type]
        campaign_id=row.get("campaign_id"),  # type: ignore[arg-type]
        event_seq=event_seq,
        posted_at=row["posted_at"],  # type: ignore[arg-type]
    )


class PostgresChatStore:
    def __init__(self, database_url: str) -> None:
        self._url = database_url

    def _conn(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._url)

    def create_session(
        self,
        *,
        project_id: UUID,
        tenant_id: UUID | None = None,
    ) -> ChatSessionRecord:
        now = _utc_now()
        sid = uuid4()
        tid = tenant_id or DEFAULT_TENANT_ID
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO nimbusware_chat_session (
                  session_id, tenant_id, project_id, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (sid, tid, project_id, now, now),
            )
            conn.commit()
        return ChatSessionRecord(
            session_id=sid,
            project_id=project_id,
            tenant_id=tid,
            created_at=now,
            updated_at=now,
        )

    def get_session(self, session_id: UUID) -> ChatSessionRecord | None:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM nimbusware_chat_session WHERE session_id = %s",
                (session_id,),
            )
            row = cur.fetchone()
        return _session_from_row(row) if row else None

    def list_sessions(self, *, project_id: UUID) -> list[ChatSessionRecord]:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM nimbusware_chat_session
                WHERE project_id = %s
                ORDER BY updated_at DESC
                """,
                (project_id,),
            )
            rows = cur.fetchall()
        return [_session_from_row(r) for r in rows]

    def _load_turns(
        self, cur: psycopg.Cursor[dict[str, object]], session_id: UUID
    ) -> dict[UUID, ChatTurnRecord]:
        cur.execute(
            """
            SELECT * FROM nimbusware_chat_turn
            WHERE session_id = %s
            ORDER BY ordinal ASC
            """,
            (session_id,),
        )
        return {UUID(str(r["turn_id"])): _turn_from_row(r) for r in cur.fetchall()}

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
        role_n = _validate_role(role)
        now = _utc_now()
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM nimbusware_chat_session WHERE session_id = %s FOR UPDATE",
                (session_id,),
            )
            session_row = cur.fetchone()
            if session_row is None:
                raise KeyError("chat_session_not_found")
            assert isinstance(session_row, dict)
            session = _session_from_row(session_row)
            parent = parent_turn_id or session.active_leaf_turn_id
            cur.execute(
                "SELECT COALESCE(MAX(ordinal), 0) + 1 AS n FROM nimbusware_chat_turn WHERE session_id = %s",
                (session_id,),
            )
            ord_row = cur.fetchone()
            assert isinstance(ord_row, dict)
            ordinal = int(ord_row["n"])
            turn_id = uuid4()
            cur.execute(
                """
                INSERT INTO nimbusware_chat_turn (
                  turn_id, session_id, parent_turn_id, ordinal, role, text, payload,
                  work_type, work_type_source, run_id, campaign_id, event_seq, posted_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s)
                """,
                (
                    turn_id,
                    session_id,
                    parent,
                    ordinal,
                    role_n,
                    text,
                    Jsonb(dict(payload or {})),
                    work_type,
                    work_type_source,
                    run_id,
                    campaign_id,
                    event_seq,
                    now,
                ),
            )
            root = session.root_turn_id or turn_id
            title = session.title
            if title is None and role_n == "user" and text.strip():
                title = text.strip()[:120]
            cur.execute(
                """
                UPDATE nimbusware_chat_session SET
                  updated_at = %s,
                  root_turn_id = %s,
                  active_leaf_turn_id = %s,
                  title = COALESCE(%s, title),
                  run_id = COALESCE(%s, run_id),
                  campaign_id = COALESCE(%s, campaign_id)
                WHERE session_id = %s
                """,
                (now, root, turn_id, title, run_id, campaign_id, session_id),
            )
            conn.commit()
        return ChatTurnRecord(
            turn_id=turn_id,
            session_id=session_id,
            parent_turn_id=parent,
            ordinal=ordinal,
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

    def fork_at_turn(self, session_id: UUID, turn_id: UUID) -> ChatSessionRecord:
        now = _utc_now()
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT 1 FROM nimbusware_chat_turn WHERE session_id = %s AND turn_id = %s",
                (session_id, turn_id),
            )
            if cur.fetchone() is None:
                raise KeyError("chat_turn_not_found")
            cur.execute(
                """
                UPDATE nimbusware_chat_session
                SET active_leaf_turn_id = %s, updated_at = %s
                WHERE session_id = %s
                RETURNING *
                """,
                (turn_id, now, session_id),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError("chat_session_not_found")
            assert isinstance(row, dict)
            conn.commit()
        return _session_from_row(row)

    def set_active_leaf(self, session_id: UUID, leaf_turn_id: UUID) -> ChatSessionRecord:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            turns = self._load_turns(cur, session_id)
            if leaf_turn_id not in turns:
                raise KeyError("chat_turn_not_found")
            children = child_turn_ids(turns, leaf_turn_id)
            if children:
                raise ValueError("active_leaf_must_be_a_branch_tip")
            now = _utc_now()
            cur.execute(
                """
                UPDATE nimbusware_chat_session
                SET active_leaf_turn_id = %s, updated_at = %s
                WHERE session_id = %s
                RETURNING *
                """,
                (leaf_turn_id, now, session_id),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError("chat_session_not_found")
            assert isinstance(row, dict)
            conn.commit()
        return _session_from_row(row)

    def update_session(
        self,
        session_id: UUID,
        *,
        last_classification: dict[str, Any] | None = None,
        work_type_override: str | None = None,
        run_id: UUID | None = None,
        campaign_id: UUID | None = None,
    ) -> ChatSessionRecord:
        now = _utc_now()
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                UPDATE nimbusware_chat_session SET
                  updated_at = %s,
                  last_classification = COALESCE(%s::jsonb, last_classification),
                  work_type_override = COALESCE(%s, work_type_override),
                  run_id = COALESCE(%s, run_id),
                  campaign_id = COALESCE(%s, campaign_id)
                WHERE session_id = %s
                RETURNING *
                """,
                (
                    now,
                    Jsonb(last_classification) if last_classification is not None else None,
                    work_type_override,
                    run_id,
                    campaign_id,
                    session_id,
                ),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError("chat_session_not_found")
            assert isinstance(row, dict)
            conn.commit()
        return _session_from_row(row)

    def get_active_path(self, session_id: UUID) -> list[ChatTurnRecord]:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT active_leaf_turn_id FROM nimbusware_chat_session WHERE session_id = %s",
                (session_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError("chat_session_not_found")
            assert isinstance(row, dict)
            leaf = row.get("active_leaf_turn_id")
            if leaf is None:
                return []
            turns = self._load_turns(cur, session_id)
        return path_to_root(turns, leaf)

    def get_graph(self, session_id: UUID) -> dict[str, Any]:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM nimbusware_chat_session WHERE session_id = %s",
                (session_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError("chat_session_not_found")
            assert isinstance(row, dict)
            session = _session_from_row(row)
            turns = self._load_turns(cur, session_id)
        return build_graph(session, turns)

    def list_turns(self, session_id: UUID) -> list[ChatTurnRecord]:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            turns = self._load_turns(cur, session_id)
        return sorted(turns.values(), key=lambda t: t.ordinal)


ChatStore = InMemoryChatStore | PostgresChatStore


def build_chat_store(database_url: str | None) -> ChatStore:
    if database_url:
        return PostgresChatStore(database_url)
    return InMemoryChatStore()
