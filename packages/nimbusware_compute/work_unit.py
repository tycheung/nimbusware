from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from nimbusware_compute.worker_policy import sanitize_work_unit_payload

WORK_UNIT_STATUSES = frozenset(
    {"queued", "assigned", "running", "ok", "failed", "timeout", "cancelled"}
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class WorkUnitRecord:
    work_unit_id: UUID
    run_id: UUID
    session_id: UUID | None
    stage_name: str
    agent_role: str
    executor_user_id: str
    status: str
    payload: dict[str, Any]
    node_id: UUID | None = None
    result: dict[str, Any] | None = None
    assigned_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None


class InMemoryWorkUnitQueue:
    """Stub queue for D2 — host enqueue/dequeue/complete without Redis yet."""

    def __init__(self) -> None:
        self._units: dict[UUID, WorkUnitRecord] = {}

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
        safe_payload = sanitize_work_unit_payload(payload)
        wid = uuid4()
        now = _utc_now()
        rec = WorkUnitRecord(
            work_unit_id=wid,
            run_id=run_id,
            session_id=session_id,
            stage_name=stage_name,
            agent_role=agent_role,
            executor_user_id=executor_user_id,
            status="queued",
            payload=safe_payload,
            created_at=now,
        )
        self._units[wid] = rec
        return rec

    def dequeue(
        self,
        *,
        session_id: UUID | None = None,
        node_id: UUID | None = None,
    ) -> WorkUnitRecord | None:
        for rec in sorted(
            self._units.values(),
            key=lambda u: u.created_at or _utc_now(),
        ):
            if rec.status != "queued":
                continue
            if session_id is not None and rec.session_id != session_id:
                continue
            assigned = WorkUnitRecord(
                work_unit_id=rec.work_unit_id,
                run_id=rec.run_id,
                session_id=rec.session_id,
                stage_name=rec.stage_name,
                agent_role=rec.agent_role,
                executor_user_id=rec.executor_user_id,
                status="assigned",
                payload=rec.payload,
                node_id=node_id,
                assigned_at=_utc_now(),
                created_at=rec.created_at,
            )
            self._units[rec.work_unit_id] = assigned
            return assigned
        return None

    def complete(
        self,
        work_unit_id: UUID,
        *,
        status: str,
        result: dict[str, Any] | None = None,
    ) -> WorkUnitRecord | None:
        rec = self._units.get(work_unit_id)
        if rec is None:
            return None
        if rec.status in {"ok", "failed", "timeout", "cancelled"}:
            return rec
        st = status if status in WORK_UNIT_STATUSES else "failed"
        done = WorkUnitRecord(
            work_unit_id=rec.work_unit_id,
            run_id=rec.run_id,
            session_id=rec.session_id,
            stage_name=rec.stage_name,
            agent_role=rec.agent_role,
            executor_user_id=rec.executor_user_id,
            status=st,
            payload=rec.payload,
            node_id=rec.node_id,
            result=dict(result) if result is not None else None,
            assigned_at=rec.assigned_at,
            completed_at=_utc_now(),
            created_at=rec.created_at,
        )
        self._units[work_unit_id] = done
        return done


def work_unit_to_public(rec: WorkUnitRecord) -> dict[str, Any]:
    return {
        "work_unit_id": str(rec.work_unit_id),
        "run_id": str(rec.run_id),
        "session_id": str(rec.session_id) if rec.session_id else None,
        "node_id": str(rec.node_id) if rec.node_id else None,
        "stage_name": rec.stage_name,
        "agent_role": rec.agent_role,
        "executor_user_id": rec.executor_user_id,
        "status": rec.status,
        "payload": rec.payload,
        "result": rec.result,
        "assigned_at": rec.assigned_at.isoformat() if rec.assigned_at else None,
        "completed_at": rec.completed_at.isoformat() if rec.completed_at else None,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }
