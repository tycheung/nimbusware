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


def emit_deploy_approved(store: Any, run_id: UUID | str) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    now = datetime.now(timezone.utc)
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata={"detail": "operator approved deploy"},
            payload=StagePassedPayload(stage_name="deploy.approved", duration_ms=0),
        ),
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


def deploy_approved_from_events(rows: list[dict[str, Any]]) -> bool:
    for row in reversed(rows):
        if row.get("event_type") != EventType.STAGE_PASSED.value:
            continue
        payload = row.get("payload")
        if isinstance(payload, dict) and payload.get("stage_name") == "deploy.approved":
            return True
    return False


def autopilot_may_auto_approve_deploy(autopilot_block: dict[str, Any] | None) -> bool:
    if not autopilot_block:
        return False
    checkpoints = autopilot_block.get("checkpoints")
    if isinstance(checkpoints, list) and "stop_before_deploy_apply" in checkpoints:
        return False
    return int(autopilot_block.get("level") or 0) >= 9


def emit_deploy_apply_stages(
    store: Any,
    run_id: UUID | str,
    result: dict[str, Any],
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    status = str(result.get("status") or "failed")
    detail = str(result.get("detail") or "")
    now = datetime.now(timezone.utc)
    meta: dict[str, Any] = {"detail": detail, "deploy": {"kind": "terraform_apply"}}
    for key in ("api_url", "web_url", "live_urls"):
        if result.get(key):
            meta[key] = result[key]
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata=meta,
            payload=StageStartedPayload(stage_name="deploy.started", attempt=1),
        ),
    )
    if status == "skipped":
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata={**meta, "detail": detail or "apply skipped"},
                payload=StagePassedPayload(stage_name="deploy.apply", duration_ms=0),
            ),
        )
        return
    if status == "passed":
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=now,
                metadata=meta,
                payload=StagePassedPayload(stage_name="deploy.apply", duration_ms=0),
            ),
        )
        return
    store.append(
        StageFailedEvent(
            event_type=EventType.STAGE_FAILED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata={**meta, "stderr": result.get("stderr", "")},
            payload=StageFailedPayload(
                stage_name="deploy.apply",
                reason_code="terraform_apply_failed",
                message=detail[:500],
            ),
        ),
    )
