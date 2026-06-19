from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from nimbusware_iam.constants import DEFAULT_TENANT_ID
from nimbusware_maker.chat_models import ChatSessionRecord, ChatTurnRecord
from nimbusware_maker.chat_store_graph import (
    _validate_role,
    build_graph,
    child_turn_ids,
    path_to_root,
)
from nimbusware_maker.chat_store_rows import (
    _UNSET,
    _session_from_row,
    _turn_from_row,
    _utc_now,
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
        host_user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChatSessionRecord:
        now = _utc_now()
        sid = uuid4()
        tid = tenant_id or DEFAULT_TENANT_ID
        meta = dict(metadata or {})
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO nimbusware_chat_session (
                  session_id, tenant_id, project_id, host_user_id, metadata, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
                """,
                (sid, tid, project_id, host_user_id, Jsonb(meta), now, now),
            )
            conn.commit()
        return ChatSessionRecord(
            session_id=sid,
            project_id=project_id,
            tenant_id=tid,
            created_at=now,
            updated_at=now,
            host_user_id=host_user_id,
            metadata=meta,
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

    def find_session_by_run_id(self, run_id: UUID) -> ChatSessionRecord | None:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM nimbusware_chat_session
                WHERE run_id = %s
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (run_id,),
            )
            row = cur.fetchone()
        return _session_from_row(row) if row else None

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
        host_user_id: UUID | None = None,
        workload_distribution: str | None = None,
        folder_id: UUID | None | Any = _UNSET,
        tags: list[str] | None | Any = _UNSET,
        metadata: dict[str, Any] | None = None,
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
                  campaign_id = COALESCE(%s, campaign_id),
                  host_user_id = COALESCE(%s, host_user_id),
                  workload_distribution = COALESCE(%s, workload_distribution),
                  folder_id = CASE WHEN %s THEN %s ELSE folder_id END,
                  tags = CASE WHEN %s THEN %s::text[] ELSE tags END,
                  metadata = COALESCE(%s::jsonb, metadata)
                WHERE session_id = %s
                RETURNING *
                """,
                (
                    now,
                    Jsonb(last_classification) if last_classification is not None else None,
                    work_type_override,
                    run_id,
                    campaign_id,
                    host_user_id,
                    workload_distribution,
                    folder_id is not _UNSET,
                    folder_id if folder_id is not _UNSET else None,
                    tags is not _UNSET,
                    list(tags or []) if tags is not _UNSET else None,
                    Jsonb(metadata) if metadata is not None else None,
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

    def list_recent_analytics_turn_rows(
        self,
        *,
        limit_sessions: int = 500,
    ) -> list[dict[str, Any]]:
        cap = max(1, min(limit_sessions, 5000))
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                WITH recent AS (
                  SELECT session_id
                  FROM nimbusware_chat_session
                  ORDER BY updated_at DESC
                  LIMIT %s
                )
                SELECT
                  t.turn_id, t.session_id, t.parent_turn_id, t.ordinal, t.role,
                  t.text, t.payload, t.work_type, t.work_type_source,
                  t.run_id, t.campaign_id, t.event_seq, t.posted_at,
                  s.project_id
                FROM nimbusware_chat_turn t
                JOIN recent r ON r.session_id = t.session_id
                JOIN nimbusware_chat_session s ON s.session_id = t.session_id
                ORDER BY t.posted_at ASC
                """,
                (cap,),
            )
            rows = cur.fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            assert isinstance(row, dict)
            out.append(
                {
                    "turn_id": str(row["turn_id"]),
                    "session_id": str(row["session_id"]),
                    "parent_turn_id": (
                        str(row["parent_turn_id"]) if row.get("parent_turn_id") else None
                    ),
                    "ordinal": int(row["ordinal"]),
                    "role": str(row["role"]),
                    "text": str(row["text"]),
                    "payload": row["payload"],
                    "work_type": row.get("work_type"),
                    "work_type_source": row.get("work_type_source"),
                    "run_id": str(row["run_id"]) if row.get("run_id") else None,
                    "campaign_id": str(row["campaign_id"]) if row.get("campaign_id") else None,
                    "event_seq": row.get("event_seq"),
                    "posted_at": row.get("posted_at"),
                    "project_id": str(row["project_id"]),
                }
            )
        return out
