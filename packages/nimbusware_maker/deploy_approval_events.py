from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, StagePassedEvent
from agent_core.models.events_payloads import StagePassedPayload
from nimbusware_maker.deploy_approval_enforcement import deploy_dual_control_satisfied


def emit_deploy_approved(
    store: Any,
    run_id: UUID | str,
    *,
    approver_user_id: str | None = None,
    approval_kind: str = "maker",
) -> None:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    now = datetime.now(timezone.utc)
    meta: dict[str, Any] = {"detail": "operator approved deploy", "approval_kind": approval_kind}
    if approver_user_id:
        meta["approver_user_id"] = approver_user_id
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata=meta,
            payload=StagePassedPayload(stage_name="deploy.approved", duration_ms=0),
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


def deploy_apply_ready(
    rows: list[dict[str, Any]], *, deploy_approval_chain: str = "maker_only"
) -> bool:
    chain = (deploy_approval_chain or "maker_only").strip()
    if not deploy_approved_from_events(rows):
        return False
    if chain == "dual_control":
        return deploy_dual_control_satisfied(rows)
    return True


def autopilot_may_auto_approve_deploy(autopilot_block: dict[str, Any] | None) -> bool:
    if not autopilot_block:
        return False
    checkpoints = autopilot_block.get("checkpoints")
    if isinstance(checkpoints, list) and "stop_before_deploy_apply" in checkpoints:
        return False
    return int(autopilot_block.get("level") or 0) >= 9
