from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest

from agent_core.models import EventType, StageFailedEvent, StageFailedPayload
from nimbusware_orchestrator.pipeline import make_dev_orchestrator


def test_cumulative_stage_failures_emits_single_escalation() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    for i in range(2):
        mem.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=datetime.now(timezone.utc),
                payload=StageFailedPayload(
                    stage_name=f"other:{i}",
                    reason_code="x",
                    message="m",
                ),
            ),
        )
    with patch(
        "nimbusware_orchestrator._pipeline.escalation.load_escalate_after_cumulative_stage_failures",
        return_value=2,
    ):
        orch._maybe_escalate_after_cumulative_stage_failures(rid)
        orch._maybe_escalate_after_cumulative_stage_failures(rid)
    esc = [
        r for r in mem.list_run_events(str(rid)) if r["event_type"] == EventType.RUN_ESCALATED.value
    ]
    assert len(esc) == 1
    assert (esc[0].get("payload") or {}).get("reason_code") == "cumulative_stage_failures"


def test_cumulative_stage_escalation_suppressed_by_workflow() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("escalation_suppress_on")
    for i in range(2):
        mem.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=datetime.now(timezone.utc),
                payload=StageFailedPayload(
                    stage_name=f"other:{i}",
                    reason_code="x",
                    message="m",
                ),
            ),
        )
    with patch(
        "nimbusware_orchestrator._pipeline.escalation.load_escalate_after_cumulative_stage_failures",
        return_value=2,
    ):
        orch._maybe_escalate_after_cumulative_stage_failures(rid)
    assert not any(
        r["event_type"] == EventType.RUN_ESCALATED.value for r in mem.list_run_events(str(rid))
    )


@pytest.mark.parametrize("n_failures", [0, 1])
def test_cumulative_stage_failures_below_threshold_no_escalation(n_failures: int) -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    for i in range(n_failures):
        mem.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=datetime.now(timezone.utc),
                payload=StageFailedPayload(
                    stage_name=f"other:{i}",
                    reason_code="x",
                    message="m",
                ),
            ),
        )
    with patch(
        "nimbusware_orchestrator._pipeline.escalation.load_escalate_after_cumulative_stage_failures",
        return_value=2,
    ):
        orch._maybe_escalate_after_cumulative_stage_failures(rid)
    assert not any(
        r["event_type"] == EventType.RUN_ESCALATED.value for r in mem.list_run_events(str(rid))
    )
