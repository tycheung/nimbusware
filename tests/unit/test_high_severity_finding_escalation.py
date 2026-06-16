from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    FindingCreatedEvent,
    FindingCreatedPayload,
    Severity,
)
from nimbusware_orchestrator.pipeline import make_dev_orchestrator

_BACKEND_WRITER = UUID("44444444-4444-4444-8444-444444444404")


def _high_finding_payload(orch: object, run_id: UUID) -> FindingCreatedPayload:
    writer = orch._registry.resolve("backend_writer")  # noqa: SLF001
    ctx = orch._strictness_context(run_id)  # noqa: SLF001
    fix = {
        "format": "unified_diff",
        "target_files": ["a.py"],
        "patch_artifact": "{}",
        "validation_steps": ["pytest"],
        "acceptance_criteria": "green",
    }
    return FindingCreatedPayload.model_validate(
        {
            "finding_id": str(uuid4()),
            "category": "test",
            "owner_role": str(writer),
            "severity": Severity.HIGH.value,
            "source_artifact": "unit",
            "repro_steps": ["x"],
            "required_fixes": [fix],
        },
        context=ctx,
    )


def test_cumulative_high_severity_findings_emits_single_escalation() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    for _ in range(2):
        mem.append(
            FindingCreatedEvent(
                event_type=EventType.FINDING_CREATED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=datetime.now(timezone.utc),
                payload=_high_finding_payload(orch, rid),
            ),
        )
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_after_cumulative_high_severity_findings",
        return_value=2,
    ):
        orch._maybe_escalate_after_cumulative_high_severity_findings(rid)  # noqa: SLF001
        orch._maybe_escalate_after_cumulative_high_severity_findings(rid)  # noqa: SLF001
    esc = [
        r for r in mem.list_run_events(str(rid)) if r["event_type"] == EventType.RUN_ESCALATED.value
    ]
    assert len(esc) == 1
    assert (esc[0].get("payload") or {}).get("reason_code") == "cumulative_high_severity_findings"


def test_high_severity_finding_escalation_suppressed_when_workflow_suppresses() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("escalation_suppress_on")
    for _ in range(2):
        mem.append(
            FindingCreatedEvent(
                event_type=EventType.FINDING_CREATED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=datetime.now(timezone.utc),
                payload=_high_finding_payload(orch, rid),
            ),
        )
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_after_cumulative_high_severity_findings",
        return_value=2,
    ):
        orch._maybe_escalate_after_cumulative_high_severity_findings(rid)  # noqa: SLF001
    assert not any(
        r["event_type"] == EventType.RUN_ESCALATED.value for r in mem.list_run_events(str(rid))
    )


def test_low_severity_findings_do_not_count_toward_high_threshold() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    writer = orch._registry.resolve("backend_writer")  # noqa: SLF001
    ctx = orch._strictness_context(rid)  # noqa: SLF001
    for _ in range(3):
        low = FindingCreatedPayload.model_validate(
            {
                "finding_id": str(uuid4()),
                "category": "test",
                "owner_role": str(writer),
                "severity": Severity.LOW.value,
                "source_artifact": "unit",
                "repro_steps": ["x"],
                "required_fixes": [],
            },
            context=ctx,
        )
        mem.append(
            FindingCreatedEvent(
                event_type=EventType.FINDING_CREATED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=datetime.now(timezone.utc),
                payload=low,
            ),
        )
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_after_cumulative_high_severity_findings",
        return_value=2,
    ):
        orch._maybe_escalate_after_cumulative_high_severity_findings(rid)  # noqa: SLF001
    assert not any(
        r["event_type"] == EventType.RUN_ESCALATED.value for r in mem.list_run_events(str(rid))
    )
