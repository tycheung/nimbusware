from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from compute.work_unit import (
    WORK_UNIT_STATUSES,
    WorkUnitRecord,
    _utc_now,
)
from compute.worker_policy import sanitize_work_unit_payload


def _dt_to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _dt_from_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    return datetime.fromisoformat(raw)


def serialize_work_unit_record(rec: WorkUnitRecord) -> str:
    return json.dumps(
        {
            "work_unit_id": str(rec.work_unit_id),
            "run_id": str(rec.run_id),
            "session_id": str(rec.session_id) if rec.session_id else None,
            "stage_name": rec.stage_name,
            "agent_role": rec.agent_role,
            "executor_user_id": rec.executor_user_id,
            "status": rec.status,
            "payload": rec.payload,
            "node_id": str(rec.node_id) if rec.node_id else None,
            "result": rec.result,
            "assigned_at": _dt_to_iso(rec.assigned_at),
            "completed_at": _dt_to_iso(rec.completed_at),
            "created_at": _dt_to_iso(rec.created_at),
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def deserialize_work_unit_record(raw: str) -> WorkUnitRecord:
    data = json.loads(raw)
    return WorkUnitRecord(
        work_unit_id=UUID(str(data["work_unit_id"])),
        run_id=UUID(str(data["run_id"])),
        session_id=UUID(str(data["session_id"])) if data.get("session_id") else None,
        stage_name=str(data.get("stage_name") or ""),
        agent_role=str(data.get("agent_role") or ""),
        executor_user_id=str(data.get("executor_user_id") or ""),
        status=str(data.get("status") or "queued"),
        payload=dict(data.get("payload") or {}),
        node_id=UUID(str(data["node_id"])) if data.get("node_id") else None,
        result=dict(data["result"]) if isinstance(data.get("result"), dict) else None,
        assigned_at=_dt_from_iso(data.get("assigned_at")),
        completed_at=_dt_from_iso(data.get("completed_at")),
        created_at=_dt_from_iso(data.get("created_at")),
    )


class RedisWorkUnitQueue:
    def __init__(
        self,
        redis_url: str,
        *,
        queue_key: str = "nimbusware:compute:work_units:queue",
        records_key: str = "nimbusware:compute:work_units:records",
        client: Any | None = None,
    ) -> None:
        self._queue_key = queue_key
        self._records_key = records_key
        if client is not None:
            self._client = client
            return
        try:
            import redis
        except ImportError as exc:
            msg = "redis package is required for NIMBUSWARE_COMPUTE_WORK_QUEUE=redis"
            raise RuntimeError(msg) from exc
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def _save(self, rec: WorkUnitRecord) -> None:
        self._client.hset(self._records_key, str(rec.work_unit_id), serialize_work_unit_record(rec))

    def _load(self, work_unit_id: str) -> WorkUnitRecord | None:
        raw = self._client.hget(self._records_key, work_unit_id)
        if not raw:
            return None
        if not isinstance(raw, str):
            raw = raw.decode() if isinstance(raw, bytes) else str(raw)
        return deserialize_work_unit_record(raw)

    def list_units(self, *, run_id: UUID | None = None) -> list[WorkUnitRecord]:
        raw_map = self._client.hgetall(self._records_key)
        out: list[WorkUnitRecord] = []
        for raw in raw_map.values():
            if not isinstance(raw, str):
                raw = raw.decode() if isinstance(raw, bytes) else str(raw)
            rec = deserialize_work_unit_record(raw)
            if run_id is None or rec.run_id == run_id:
                out.append(rec)
        out.sort(key=lambda u: u.created_at or _utc_now())
        return out

    def queued_count(self, *, session_id: UUID | None = None) -> int:
        ids = self._client.lrange(self._queue_key, 0, -1)
        count = 0
        for wid in ids:
            rec = self._load(str(wid))
            if rec is None or rec.status != "queued":
                continue
            if session_id is not None and rec.session_id != session_id:
                continue
            count += 1
        return count

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
        self._save(rec)
        self._client.lpush(self._queue_key, str(wid))
        return rec

    def dequeue(
        self,
        *,
        session_id: UUID | None = None,
        node_id: UUID | None = None,
    ) -> WorkUnitRecord | None:
        depth = int(self._client.llen(self._queue_key) or 0)
        attempts = max(depth, 1)
        for _ in range(attempts):
            item = self._client.brpop(self._queue_key, timeout=1)
            if item is None:
                return None
            wid = item[1] if isinstance(item, tuple) else item
            wid_s = str(wid)
            rec = self._load(wid_s)
            if rec is None or rec.status != "queued":
                continue
            if session_id is not None and rec.session_id != session_id:
                self._client.lpush(self._queue_key, wid_s)
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
            self._save(assigned)
            return assigned
        return None

    def complete(
        self,
        work_unit_id: UUID,
        *,
        status: str,
        result: dict[str, Any] | None = None,
    ) -> WorkUnitRecord | None:
        rec = self._load(str(work_unit_id))
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
        self._save(done)
        return done

    def terminate_restart(self, work_unit_id: UUID) -> WorkUnitRecord | None:
        rec = self._load(str(work_unit_id))
        if rec is None:
            return None
        if rec.status in {"ok", "failed", "timeout", "cancelled"}:
            return None
        self.complete(work_unit_id, status="cancelled")
        return self.enqueue(
            run_id=rec.run_id,
            session_id=rec.session_id,
            stage_name=rec.stage_name,
            agent_role=rec.agent_role,
            executor_user_id=rec.executor_user_id,
            payload=dict(rec.payload),
        )

    def stats(self) -> dict[str, int]:
        return {
            "queued": int(self._client.llen(self._queue_key)),
            "records": int(self._client.hlen(self._records_key)),
        }


def get_redis_work_unit_queue(redis_url: str) -> RedisWorkUnitQueue:
    return RedisWorkUnitQueue(redis_url)


__all__ = [
    "RedisWorkUnitQueue",
    "deserialize_work_unit_record",
    "get_redis_work_unit_queue",
    "serialize_work_unit_record",
]
