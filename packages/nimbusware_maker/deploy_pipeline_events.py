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


def emit_terraform_validate_stages(
    store: Any,
    run_id: UUID | str,
    result: dict[str, Any],
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    status = str(result.get("status") or "failed")
    detail = str(result.get("detail") or "")
    plan_artifact = str(result.get("plan_artifact") or "")
    now = datetime.now(timezone.utc)

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata={"detail": detail, "deploy": {"kind": "terraform_validate"}},
            payload=StageStartedPayload(stage_name="terraform.validate", attempt=1),
        ),
    )

    meta = {
        "detail": detail,
        "plan_artifact": plan_artifact,
        "files_checked": result.get("files_checked"),
    }
    if status == "passed":
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata=meta,
                payload=StagePassedPayload(stage_name="terraform.plan", duration_ms=0),
            ),
        )
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata=meta,
                payload=StagePassedPayload(stage_name="ci.terraform", duration_ms=0),
            ),
        )
    elif status == "skipped":
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata=meta,
                payload=StagePassedPayload(stage_name="terraform.validate", duration_ms=0),
            ),
        )
    else:
        store.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata={**meta, "stderr": result.get("stderr", "")},
                payload=StageFailedPayload(
                    stage_name="terraform.validate",
                    reason_code="terraform_validate_failed",
                    message=detail[:500],
                ),
            ),
        )
