"""YAML threshold: cumulative FAIL ``gate.decision.emitted`` → one ``run.escalated``."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from agent_core.models import (
    EventType,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    Verdict,
)
from nimbusware_orchestrator.pipeline import make_dev_orchestrator


def test_cumulative_gate_failures_emits_single_escalation() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    for _ in range(2):
        mem.append(
            GateDecisionEmittedEvent(
                event_type=EventType.GATE_DECISION_EMITTED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=datetime.now(timezone.utc),
                payload=GateDecisionEmittedPayload(
                    stage_name="bundle_compatibility",
                    verdict=Verdict.FAIL,
                    unanimous_pass_required=False,
                    failure_reason_code="integrator_below_threshold",
                ),
            ),
        )
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_after_cumulative_gate_failures",
        return_value=2,
    ):
        orch._maybe_escalate_after_cumulative_gate_failures(rid)
        orch._maybe_escalate_after_cumulative_gate_failures(rid)
    esc = [
        r for r in mem.list_run_events(str(rid)) if r["event_type"] == EventType.RUN_ESCALATED.value
    ]
    assert len(esc) == 1
    assert (esc[0].get("payload") or {}).get("reason_code") == "cumulative_gate_failures"
