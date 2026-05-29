from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from agent_core.models import HermesEventUnion
from hermes_store.allowed_types import assert_event_type_registered
from hermes_store.protocol import event_row_from_serialized


def _run_list_status_fragments(
    list_status: str | None,
) -> tuple[str, str, dict[str, Any]]:
    if list_status:
        return (
            "JOIN run_list_status ls ON ls.run_id = r.run_id",
            "AND ls.list_status = %(lst)s",
            {"lst": list_status},
        )
    return ("", "", {})


_HAS_ESCALATION_SQL = """
AND (
  %(has_esc)s::boolean IS NULL
  OR (
    %(has_esc)s::boolean IS TRUE
    AND EXISTS (
      SELECT 1 FROM event_store ex
      WHERE ex.run_id = r.run_id AND ex.event_type = 'run.escalated'
    )
  )
  OR (
    %(has_esc)s::boolean IS FALSE
    AND NOT EXISTS (
      SELECT 1 FROM event_store ex
      WHERE ex.run_id = r.run_id AND ex.event_type = 'run.escalated'
    )
  )
)
"""


class PostgresEventStore:
    def __init__(self, conninfo: str) -> None:
        self._conninfo = conninfo

    def append(self, event: HermesEventUnion) -> int:
        from agent_core.models import serialize_event_persistent

        full = serialize_event_persistent(event)
        et = str(full["event_type"])
        assert_event_type_registered(et)
        row = event_row_from_serialized(full)
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO event_store (
                      event_id, run_id, stage_id, task_id, event_type, event_version,
                      occurred_at, actor_role, model_id, correlation_id, causation_id,
                      payload, metadata
                    ) VALUES (
                      %(event_id)s, %(run_id)s, %(stage_id)s, %(task_id)s, %(event_type)s,
                      %(event_version)s, %(occurred_at)s, %(actor_role)s, %(model_id)s,
                      %(correlation_id)s, %(causation_id)s, %(payload)s::jsonb,
                      %(metadata)s::jsonb
                    )
                    RETURNING store_seq
                    """,
                    {
                        "event_id": row["event_id"],
                        "run_id": row["run_id"],
                        "stage_id": row.get("stage_id"),
                        "task_id": row.get("task_id"),
                        "event_type": et,
                        "event_version": row.get("event_version", 1),
                        "occurred_at": row["occurred_at"],
                        "actor_role": row.get("actor_role"),
                        "model_id": row.get("model_id"),
                        "correlation_id": row.get("correlation_id"),
                        "causation_id": row.get("causation_id"),
                        "payload": Jsonb(row["payload"]),
                        "metadata": Jsonb(row["metadata"]),
                    },
                )
                row_out = cur.fetchone()
                assert row_out is not None
                seq = row_out[0]
            conn.commit()
        return int(seq)

    def list_run_events(self, run_id: str) -> list[dict[str, Any]]:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT store_seq, event_id, run_id, stage_id, task_id, event_type,
                           event_version, occurred_at, actor_role, model_id,
                           correlation_id, causation_id, payload, metadata
                    FROM event_store
                    WHERE run_id = %s
                    ORDER BY store_seq ASC
                    """,
                    (UUID(run_id),),
                )
                return [dict(r) for r in cur.fetchall()]

    def list_run_events_many(self, run_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        wanted = [UUID(str(r)) for r in run_ids if str(r).strip()]
        if not wanted:
            return {}
        out: dict[str, list[dict[str, Any]]] = {str(r): [] for r in wanted}
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT store_seq, event_id, run_id, stage_id, task_id, event_type,
                           event_version, occurred_at, actor_role, model_id,
                           correlation_id, causation_id, payload, metadata
                    FROM event_store
                    WHERE run_id = ANY(%s::uuid[])
                    ORDER BY run_id ASC, store_seq ASC
                    """,
                    (wanted,),
                )
                for row in cur.fetchall():
                    d = dict(row)
                    out.setdefault(str(d["run_id"]), []).append(d)
        return out

    def get_run_head(self, run_id: str) -> dict[str, Any] | None:
        rows = self.list_run_events(run_id)
        return rows[-1] if rows else None

    def max_store_seq_for_run(self, run_id: str) -> int | None:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT MAX(store_seq) FROM event_store WHERE run_id = %s",
                    (UUID(run_id),),
                )
                row = cur.fetchone()
                if row is None or row[0] is None:
                    return None
                return int(row[0])

    def find_run_id_for_run_created_correlation(self, correlation_id: UUID) -> UUID | None:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT run_id FROM event_store
                    WHERE correlation_id = %s AND event_type = 'run.created'
                    ORDER BY store_seq ASC
                    LIMIT 1
                    """,
                    (correlation_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return UUID(str(row[0]))

    def list_recent_run_ids(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        workflow_profile: str | None = None,
        workflow_profile_prefix: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        has_escalation: bool | None = None,
        list_status: str | None = None,
        order: str = "newest_first",
    ) -> list[UUID]:
        oldest = order == "oldest_first"
        if order not in ("newest_first", "oldest_first"):
            oldest = False
        ord_sql = "ASC" if oldest else "DESC"
        rid_ord = "ASC" if oldest else "DESC"
        wf_clause = (
            "(%(wf)s::text IS NULL OR LOWER(TRIM(BOTH FROM rc.wf)) = LOWER(TRIM(BOTH FROM %(wf)s::text)))"
        )
        pfx_like: str | None = None
        has_pfx = (
            workflow_profile is None
            and workflow_profile_prefix
            and str(workflow_profile_prefix).strip()
        )
        if has_pfx:
            pfx_like = str(workflow_profile_prefix).strip().lower() + "%"
        pfx_clause = (
            "(%(pfxlike)s::text IS NULL OR LOWER(TRIM(BOTH FROM rc.wf)) LIKE %(pfxlike)s::text)"
        )
        join_ls, filt_ls, extra_ls = _run_list_status_fragments(list_status)
        qparams: dict[str, Any] = {
            "wf": workflow_profile,
            "pfxlike": pfx_like,
            "ca": created_after,
            "cb": created_before,
            "has_esc": has_escalation,
            "limit": limit,
            "off": max(offset, 0),
        }
        qparams.update(extra_ls)
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    WITH ranked AS (
                      SELECT run_id, MAX(store_seq) AS mx
                      FROM event_store
                      GROUP BY run_id
                    ),
                    rc AS (
                      SELECT DISTINCT ON (e.run_id) e.run_id,
                        e.payload->>'workflow_profile' AS wf,
                        e.occurred_at AS created_at
                      FROM event_store e
                      WHERE e.event_type = 'run.created'
                      ORDER BY e.run_id, e.store_seq ASC
                    )
                    SELECT r.run_id
                    FROM ranked r
                    JOIN rc ON rc.run_id = r.run_id
                    {join_ls}
                    WHERE {wf_clause}
                      AND ({pfx_clause})
                      AND (%(ca)s::timestamptz IS NULL OR rc.created_at >= %(ca)s::timestamptz)
                      AND (%(cb)s::timestamptz IS NULL OR rc.created_at <= %(cb)s::timestamptz)
                      {_HAS_ESCALATION_SQL}
                      {filt_ls}
                    ORDER BY r.mx {ord_sql}, r.run_id {rid_ord}
                    LIMIT %(limit)s OFFSET %(off)s
                    """,
                    qparams,
                )
                return [UUID(str(r[0])) for r in cur.fetchall()]

    def list_recent_run_rows_cursor(
        self,
        *,
        limit: int,
        cursor_after_seq: int,
        cursor_after_run_id: UUID,
        workflow_profile: str | None = None,
        workflow_profile_prefix: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        has_escalation: bool | None = None,
        list_status: str | None = None,
        order: str = "newest_first",
    ) -> tuple[list[tuple[UUID, int]], bool]:
        lim = max(1, min(int(limit), 200))
        oldest = order == "oldest_first"
        if order not in ("newest_first", "oldest_first"):
            oldest = False
        ord_sql = "ASC" if oldest else "DESC"
        rid_ord = "ASC" if oldest else "DESC"
        keyset_sql = (
            "AND (r.mx > %(c_mx)s OR (r.mx = %(c_mx)s AND r.run_id > %(c_rid)s::uuid))"
            if oldest
            else "AND (r.mx < %(c_mx)s OR (r.mx = %(c_mx)s AND r.run_id < %(c_rid)s::uuid))"
        )
        wf_clause = (
            "(%(wf)s::text IS NULL OR LOWER(TRIM(BOTH FROM rc.wf)) = LOWER(TRIM(BOTH FROM %(wf)s::text)))"
        )
        pfx_like: str | None = None
        has_pfx = (
            workflow_profile is None
            and workflow_profile_prefix
            and str(workflow_profile_prefix).strip()
        )
        if has_pfx:
            pfx_like = str(workflow_profile_prefix).strip().lower() + "%"
        pfx_clause = (
            "(%(pfxlike)s::text IS NULL OR LOWER(TRIM(BOTH FROM rc.wf)) LIKE %(pfxlike)s::text)"
        )
        fetch = lim + 1
        join_ls, filt_ls, extra_ls = _run_list_status_fragments(list_status)
        qparams: dict[str, Any] = {
            "wf": workflow_profile,
            "pfxlike": pfx_like,
            "ca": created_after,
            "cb": created_before,
            "has_esc": has_escalation,
            "fetch": fetch,
            "c_mx": int(cursor_after_seq),
            "c_rid": cursor_after_run_id,
        }
        qparams.update(extra_ls)
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    WITH ranked AS (
                      SELECT run_id, MAX(store_seq) AS mx
                      FROM event_store
                      GROUP BY run_id
                    ),
                    rc AS (
                      SELECT DISTINCT ON (e.run_id) e.run_id,
                        e.payload->>'workflow_profile' AS wf,
                        e.occurred_at AS created_at
                      FROM event_store e
                      WHERE e.event_type = 'run.created'
                      ORDER BY e.run_id, e.store_seq ASC
                    )
                    SELECT r.run_id, r.mx
                    FROM ranked r
                    JOIN rc ON rc.run_id = r.run_id
                    {join_ls}
                    WHERE {wf_clause}
                      AND ({pfx_clause})
                      AND (%(ca)s::timestamptz IS NULL OR rc.created_at >= %(ca)s::timestamptz)
                      AND (%(cb)s::timestamptz IS NULL OR rc.created_at <= %(cb)s::timestamptz)
                      {_HAS_ESCALATION_SQL}
                      {filt_ls}
                      {keyset_sql}
                    ORDER BY r.mx {ord_sql}, r.run_id {rid_ord}
                    LIMIT %(fetch)s
                    """,
                    qparams,
                )
                raw = [(UUID(str(r[0])), int(r[1])) for r in cur.fetchall()]
        has_more = len(raw) > lim
        return raw[:lim], has_more

    def count_recent_runs(
        self,
        *,
        workflow_profile: str | None = None,
        workflow_profile_prefix: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        has_escalation: bool | None = None,
        list_status: str | None = None,
    ) -> int:
        wf_clause = (
            "(%(wf)s::text IS NULL OR LOWER(TRIM(BOTH FROM rc.wf)) = LOWER(TRIM(BOTH FROM %(wf)s::text)))"
        )
        pfx_like: str | None = None
        has_pfx = (
            workflow_profile is None
            and workflow_profile_prefix
            and str(workflow_profile_prefix).strip()
        )
        if has_pfx:
            pfx_like = str(workflow_profile_prefix).strip().lower() + "%"
        pfx_clause = (
            "(%(pfxlike)s::text IS NULL OR LOWER(TRIM(BOTH FROM rc.wf)) LIKE %(pfxlike)s::text)"
        )
        join_ls, filt_ls, extra_ls = _run_list_status_fragments(list_status)
        qparams: dict[str, Any] = {
            "wf": workflow_profile,
            "pfxlike": pfx_like,
            "ca": created_after,
            "cb": created_before,
            "has_esc": has_escalation,
        }
        qparams.update(extra_ls)
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    WITH ranked AS (
                      SELECT run_id, MAX(store_seq) AS mx
                      FROM event_store
                      GROUP BY run_id
                    ),
                    rc AS (
                      SELECT DISTINCT ON (e.run_id) e.run_id,
                        e.payload->>'workflow_profile' AS wf,
                        e.occurred_at AS created_at
                      FROM event_store e
                      WHERE e.event_type = 'run.created'
                      ORDER BY e.run_id, e.store_seq ASC
                    )
                    SELECT COUNT(*)::bigint
                    FROM ranked r
                    JOIN rc ON rc.run_id = r.run_id
                    {join_ls}
                    WHERE {wf_clause}
                      AND ({pfx_clause})
                      AND (%(ca)s::timestamptz IS NULL OR rc.created_at >= %(ca)s::timestamptz)
                      AND (%(cb)s::timestamptz IS NULL OR rc.created_at <= %(cb)s::timestamptz)
                      {_HAS_ESCALATION_SQL}
                      {filt_ls}
                    """,
                    qparams,
                )
                row = cur.fetchone()
                return int(row[0]) if row and row[0] is not None else 0
