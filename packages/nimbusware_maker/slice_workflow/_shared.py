from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    StagePassedEvent,
    StagePassedPayload,
    StageStartedEvent,
    StageStartedPayload,
)
from nimbusware_maker.slice_engine import SlicePlan, parse_slice_plan


def emit_maker_stage(
    orch: Any,
    run_id: UUID,
    stage_name: str,
    metadata: dict[str, Any],
) -> None:
    meta = {**metadata, "maker_approval": True}
    now = datetime.now(timezone.utc)
    orch._store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            metadata=meta,
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    orch._store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=meta,
            payload=StagePassedPayload(stage_name=stage_name, duration_ms=0),
        ),
    )


def completed_slice_count(rows: list[dict[str, Any]]) -> int:
    count = 0
    seen: set[str] = set()
    for row in rows:
        if row.get("event_type") != EventType.STAGE_PASSED.value:
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        if payload.get("stage_name") != "slice.gate":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        if meta.get("slice_gate_verdict") != "PASS":
            continue
        sid = str(meta.get("slice_id") or "")
        if sid and sid not in seen:
            seen.add(sid)
            count += 1
    return count


def plan_from_pending(pending: dict[str, Any]) -> SlicePlan:
    raw = pending.get("slice_plan")
    if isinstance(raw, dict):
        return parse_slice_plan(raw)
    return parse_slice_plan(
        {
            "slice_id": pending.get("slice_id", "slice-1"),
            "rationale": pending.get("rationale", ""),
            "target_paths": pending.get("target_paths") or [],
            "acceptance_criteria": "",
        },
    )
