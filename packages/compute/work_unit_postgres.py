from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from compute.work_unit import (
    WORK_UNIT_STATUSES,
    WorkUnitRecord,
    _refuse_direct_queue_op,
    _utc_now,
)
from compute.worker_policy import sanitize_work_unit_payload
from iam.constants import DEFAULT_TENANT_ID

_SELECT_COLS = """
    work_unit_id, run_id, session_id, node_id, stage_name, agent_role,
    executor_user_id, status, payload, result, assigned_at, completed_at, created_at
"""


def _row_to_record(row: dict[str, Any]) -> WorkUnitRecord:
    payload = row.get("payload")
    result = row.get("result")
    return WorkUnitRecord(
        work_unit_id=row["work_unit_id"],
        run_id=row["run_id"],
        session_id=row.get("session_id"),
        stage_name=str(row.get("stage_name") or ""),
        agent_role=str(row.get("agent_role") or ""),
        executor_user_id=str(row.get("executor_user_id") or ""),
        status=str(row.get("status") or "queued"),
        payload=dict(payload) if isinstance(payload, dict) else {},
        node_id=row.get("node_id"),
        result=dict(result) if isinstance(result, dict) else None,
        assigned_at=row.get("assigned_at"),
        completed_at=row.get("completed_at"),
        created_at=row.get("created_at"),
    )


class PostgresWorkUnitQueue:
    def __init__(self, conninfo: str, *, tenant_id: UUID | None = None) -> None:
        # sak439-i: defense-in-depth refuse under COMPUTE peel.
        from broker_client.flags import broker_compute_enabled

        if broker_compute_enabled():
            raise RuntimeError(
                "compute PostgresWorkUnitQueue unavailable under "
                "NIMBUSWARE_BROKER_COMPUTE=1|2; use SwissArmyNoife compute_work"
            )
        self._conninfo = conninfo
        self._tenant_id = tenant_id or DEFAULT_TENANT_ID

    def list_units(self, *, run_id: UUID | None = None) -> list[WorkUnitRecord]:
        _refuse_direct_queue_op("list_units")  # sak491-a
        with psycopg.connect(self._conninfo) as conn, conn.cursor(row_factory=dict_row) as cur:
            if run_id is None:
                cur.execute(
                    f"SELECT {_SELECT_COLS} FROM nimbusware_work_unit ORDER BY created_at ASC",
                )
            else:
                cur.execute(
                    f"""
                    SELECT {_SELECT_COLS}
                    FROM nimbusware_work_unit
                    WHERE run_id = %s
                    ORDER BY created_at ASC
                    """,
                    (run_id,),
                )
            rows = cur.fetchall()
        return [_row_to_record(dict(r)) for r in rows]

    def queued_count(self, *, session_id: UUID | None = None) -> int:
        _refuse_direct_queue_op("queued_count")  # sak491-a
        with psycopg.connect(self._conninfo) as conn, conn.cursor() as cur:
            if session_id is None:
                cur.execute(
                    "SELECT COUNT(*) FROM nimbusware_work_unit WHERE status = 'queued'",
                )
            else:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM nimbusware_work_unit
                    WHERE status = 'queued' AND session_id = %s
                    """,
                    (session_id,),
                )
            row = cur.fetchone()
        return int(row[0] if row else 0)

    def enqueue(
        self,
        *,
        run_id: UUID,
        stage_name: str,
        session_id: UUID | None = None,
        agent_role: str = "",
        executor_user_id: str = "",
        payload: dict[str, Any] | None = None,
    ) -> WorkUnitRecord:
        _refuse_direct_queue_op("enqueue")  # sak490-b
        safe_payload = sanitize_work_unit_payload(payload)
        wid = uuid4()
        now = _utc_now()
        with psycopg.connect(self._conninfo) as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                INSERT INTO nimbusware_work_unit (
                  work_unit_id, tenant_id, run_id, session_id, stage_name, agent_role,
                  executor_user_id, status, payload, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'queued', %s::jsonb, %s)
                RETURNING {_SELECT_COLS}
                """,
                (
                    wid,
                    self._tenant_id,
                    run_id,
                    session_id,
                    stage_name,
                    agent_role,
                    executor_user_id,
                    Jsonb(safe_payload),
                    now,
                ),
            )
            row = cur.fetchone()
            conn.commit()
        assert row is not None
        return _row_to_record(dict(row))

    def dequeue(
        self,
        *,
        session_id: UUID | None = None,
        node_id: UUID | None = None,
    ) -> WorkUnitRecord | None:
        _refuse_direct_queue_op("dequeue")  # sak490-b
        with psycopg.connect(self._conninfo) as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                UPDATE nimbusware_work_unit
                SET status = 'assigned', node_id = %s, assigned_at = NOW()
                WHERE work_unit_id = (
                  SELECT work_unit_id FROM nimbusware_work_unit
                  WHERE status = 'queued'
                    AND (%s::uuid IS NULL OR session_id = %s)
                  ORDER BY created_at ASC
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1
                )
                RETURNING {_SELECT_COLS}
                """,
                (node_id, session_id, session_id),
            )
            row = cur.fetchone()
            conn.commit()
        if row is None:
            return None
        return _row_to_record(dict(row))

    def complete(
        self,
        work_unit_id: UUID,
        *,
        status: str,
        result: dict[str, Any] | None = None,
    ) -> WorkUnitRecord | None:
        _refuse_direct_queue_op("complete")  # sak490-b
        st = status if status in WORK_UNIT_STATUSES else "failed"
        with psycopg.connect(self._conninfo) as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                UPDATE nimbusware_work_unit
                SET status = %s,
                    result = COALESCE(%s::jsonb, result),
                    completed_at = NOW()
                WHERE work_unit_id = %s
                  AND status NOT IN ('ok', 'failed', 'timeout', 'cancelled')
                RETURNING {_SELECT_COLS}
                """,
                (
                    st,
                    Jsonb(dict(result)) if result is not None else None,
                    work_unit_id,
                ),
            )
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    f"SELECT {_SELECT_COLS} FROM nimbusware_work_unit WHERE work_unit_id = %s",
                    (work_unit_id,),
                )
                row = cur.fetchone()
            conn.commit()
        if row is None:
            return None
        return _row_to_record(dict(row))

    def terminate_restart(self, work_unit_id: UUID) -> WorkUnitRecord | None:
        _refuse_direct_queue_op("terminate_restart")  # sak491-a
        with psycopg.connect(self._conninfo) as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT status FROM nimbusware_work_unit WHERE work_unit_id = %s",
                (work_unit_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            if str(row.get("status") or "") in {"ok", "failed", "timeout", "cancelled"}:
                return None
        rec = self.complete(work_unit_id, status="cancelled")
        if rec is None:
            return None
        return self.enqueue(
            run_id=rec.run_id,
            session_id=rec.session_id,
            stage_name=rec.stage_name,
            agent_role=rec.agent_role,
            executor_user_id=rec.executor_user_id,
            payload=dict(rec.payload),
        )
