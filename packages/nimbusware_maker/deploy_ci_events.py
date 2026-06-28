from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, StageFailedEvent, StagePassedEvent, StageStartedEvent
from agent_core.models.events_payloads import (
    StageFailedPayload,
    StagePassedPayload,
    StageStartedPayload,
)


def emit_ci_workflow_stages(
    store: Any,
    run_id: UUID | str,
    result: dict[str, Any],
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    status = str(result.get("status") or "failed")
    detail = str(result.get("detail") or "")
    now = datetime.now(timezone.utc)
    meta: dict[str, Any] = {"detail": detail, "ci": {"kind": "github_workflow"}}
    for key in ("run_url", "workflow_run_id", "github_status", "conclusion"):
        if result.get(key):
            meta[key] = result[key]
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata=meta,
            payload=StageStartedPayload(stage_name="ci.workflow.started", attempt=1),
        ),
    )
    if status == "skipped":
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata={**meta, "detail": detail or "workflow poll skipped"},
                payload=StagePassedPayload(stage_name="ci.workflow", duration_ms=0),
            ),
        )
        return
    if status == "running":
        return
    if status == "passed":
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata=meta,
                payload=StagePassedPayload(stage_name="ci.workflow", duration_ms=0),
            ),
        )
        return
    store.append(
        StageFailedEvent(
            event_type=EventType.STAGE_FAILED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata=meta,
            payload=StageFailedPayload(
                stage_name="ci.workflow",
                reason_code="ci_workflow_failed",
                message=detail[:500],
            ),
        ),
    )
