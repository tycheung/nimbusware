"""``_workflow_suppresses_automatic_escalation`` cross-path suppress matrix.

fo87's Next-slice item (5) surfaced this exact gap. The guard at
[pipeline.py:1244-1248](d:\\Hermes\\packages\\hermes_orchestrator\\pipeline.py)
is called by **6** escalation ``_maybe_*`` paths, but only **1**
(``_maybe_escalate_after_cumulative_stage_failures``) has a
suppress test today. The remaining 5 paths are unpinned for the
suppress fork; one of them (``_maybe_auto_escalate``) has zero
direct tests at all (only its loader is covered).

fo88 closes the gap via 3 parts spanning 14 contract axes:

* **Part A** locks the 5 direct-guard contract axes:

 - Bare ``default`` workflow -> ``False``.
 - ``escalation_suppress_on`` profile -> ``True`` (central True-arm).
 - Empty store random run_id -> ``False`` (helper returns
 ``None`` -> ``parse_escalation_workflow_block`` default off
 per "missing block does not suppress" docstring).
 - Same run_id with only non-``RUN_CREATED`` rows -> ``False``
 (pins the ``event_type == "run.created"`` filter).
 - Per-run isolation: same orchestrator with two different
 workflow profiles returns the correct value per run.

* **Part B** locks the 5 unpinned ``_maybe_*`` caller paths:

 - ``_maybe_emit_anti_deadlock_escalation`` (B1)
 - ``_maybe_escalate_after_cumulative_gate_failures`` (B2)
 - ``_maybe_auto_escalate`` (B3) -- includes a **control
 sub-axis** providing the first direct base test for this
 method (the suppress vs non-suppress fork proves both halves).
 - ``_maybe_notice_escalate_findings`` (B4)
 - ``_maybe_escalate_verifier_failure_checkpoint`` (B5)

 Each axis sets up "would-trigger" conditions on the
 ``escalation_suppress_on`` workflow and asserts **zero**
 ``RUN_ESCALATED`` rows. Uses ``unittest.mock.patch`` at the
 ``hermes_orchestrator.pipeline.<loader>`` import site (mirrors
 ``test_cumulative_stage_failure_escalation.py``).

* **Part C** locks the 4 ``workflow_profile_from_run_created_rows``
 helper axes (the underlying primitive the guard depends on):

 - Empty rows list -> ``None``.
 - Rows but no ``run.created`` -> ``None``.
 - Single ``run.created`` -> returns ``payload.workflow_profile``.
 - Two ``run.created`` rows -> **FIRST** in iteration order wins.

After fo88: **6/6 escalation paths have suppress coverage**;
``_maybe_auto_escalate`` gets its first direct test; the guard
itself has a 5-axis direct contract; the underlying profile
helper has a 4-axis matrix.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import patch
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    FindingCreatedEvent,
    FindingCreatedPayload,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    RunStartedEvent,
    RunStartedPayload,
    Severity,
    Verdict,
)
from hermes_orchestrator.integrator_gate import workflow_profile_from_run_created_rows
from hermes_orchestrator.pipeline import make_dev_orchestrator

if TYPE_CHECKING:
    from hermes_store.memory import InMemoryEventStore

_RUN_ESCALATED = "run.escalated"

_BACKEND_WRITER = UUID("44444444-4444-4444-8444-444444444404")


def _run_escalated_reasons(mem: InMemoryEventStore, run_id: UUID) -> list[str]:
    """Return ``reason_code`` values for RUN_ESCALATED rows for the run, in order."""
    return [
        (r.get("payload") or {}).get("reason_code")
        for r in mem.list_run_events(str(run_id))
        if r["event_type"] == _RUN_ESCALATED
    ]


def _append_fail_gate_row(
    mem: InMemoryEventStore,
    run_id: UUID,
    stage_name: str,
) -> None:
    """Append a synthetic FAIL ``gate.decision.emitted`` row for the run."""
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name=stage_name,
                verdict=Verdict.FAIL,
                failure_reason_code="fo88_synthetic_fail",
            ),
        ),
    )


def _append_finding_row(mem: InMemoryEventStore, run_id: UUID) -> None:
    """Append a synthetic LOW-severity ``finding.created`` row for the run."""
    mem.append(
        FindingCreatedEvent(
            event_type=EventType.FINDING_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=FindingCreatedPayload(
                finding_id=uuid4(),
                category="fo88_synthetic",
                owner_role=_BACKEND_WRITER,
                severity=Severity.LOW,
                source_artifact="fo88",
                repro_steps=[],
                required_fixes=[],
            ),
        ),
    )


def test_workflow_suppresses_automatic_escalation_direct_contract_5_axis() -> None:
    """Pin the guard at pipeline.py:1244-1248 directly.

    Axis A1 -- bare ``default`` -> ``False``.
    Axis A2 -- ``escalation_suppress_on`` -> ``True`` (central
    True-arm; profile workflow YAML sets
    ``escalation.suppress_automatic_escalation: true``).
    Axis A3 -- empty store random run_id -> ``False`` (helper
    returns ``None`` -> ``parse_escalation_workflow_block`` default
    block; mirrors "missing block does not suppress" docstring).
    Axis A4 -- same run_id with only non-RUN_CREATED rows ->
    ``False`` (pins the ``event_type == "run.created"`` filter
    in ``workflow_profile_from_run_created_rows``).
    Axis A5 -- per-run isolation: two runs with different profiles
    on the same orchestrator return different values (pins per-run
    lookup, not cached orchestrator state).
    """
    orch_a1, _ = make_dev_orchestrator()
    rid_a1 = orch_a1.create_run("default")
    assert orch_a1._workflow_suppresses_automatic_escalation(rid_a1) is False  # noqa: SLF001

    orch_a2, _ = make_dev_orchestrator()
    rid_a2 = orch_a2.create_run("escalation_suppress_on")
    assert orch_a2._workflow_suppresses_automatic_escalation(rid_a2) is True, (  # noqa: SLF001
        "escalation_suppress_on workflow must yield True at the central guard"
    )

    orch_a3, _ = make_dev_orchestrator()
    assert orch_a3._workflow_suppresses_automatic_escalation(uuid4()) is False, (  # noqa: SLF001
        "empty store / unknown run_id should fall back to the default block (no suppress)"
    )

    orch_a4, mem_a4 = make_dev_orchestrator()
    rid_a4 = uuid4()
    mem_a4.append(
        RunStartedEvent(
            event_type=EventType.RUN_STARTED,
            event_id=uuid4(),
            run_id=rid_a4,
            occurred_at=datetime.now(timezone.utc),
            payload=RunStartedPayload(started_by="fo88-test"),
        ),
    )
    assert orch_a4._workflow_suppresses_automatic_escalation(rid_a4) is False, (  # noqa: SLF001
        "rows with only RUN_STARTED (no RUN_CREATED) must yield False "
        "via workflow_profile_from_run_created_rows -> None"
    )

    orch_a5, _ = make_dev_orchestrator()
    rid_default = orch_a5.create_run("default")
    rid_suppress = orch_a5.create_run("escalation_suppress_on")
    assert orch_a5._workflow_suppresses_automatic_escalation(rid_default) is False  # noqa: SLF001
    assert orch_a5._workflow_suppresses_automatic_escalation(rid_suppress) is True, (  # noqa: SLF001
        "per-run isolation broken: each run_id must resolve its own workflow profile"
    )


def test_workflow_suppress_matrix_across_unpinned_maybe_callers_5_axis() -> None:
    """Pin the suppress fork for the 5 unpinned escalation ``_maybe_*`` paths.

    Each axis sets up the "would-trigger" conditions on the
    ``escalation_suppress_on`` workflow and asserts the suppress
    guard short-circuits before any RUN_ESCALATED row is appended.

    B1 -- ``_maybe_emit_anti_deadlock_escalation``
    B2 -- ``_maybe_escalate_after_cumulative_gate_failures``
    B3 -- ``_maybe_auto_escalate`` (suppress + first direct
    control axis -- this method had zero direct test coverage
    before fo88).
    B4 -- ``_maybe_notice_escalate_findings``
    B5 -- ``_maybe_escalate_verifier_failure_checkpoint``
    """
    orch_b1, mem_b1 = make_dev_orchestrator()
    rid_b1 = orch_b1.create_run("escalation_suppress_on")
    with (
        patch(
            "hermes_orchestrator.pipeline.load_anti_deadlock_settings",
            return_value=(True, 0, 0),
        ),
        patch(
            "hermes_orchestrator.pipeline.should_emit_anti_deadlock_escalation",
            return_value=True,
        ),
    ):
        orch_b1._maybe_emit_anti_deadlock_escalation(rid_b1)  # noqa: SLF001
    assert _run_escalated_reasons(mem_b1, rid_b1) == [], (
        "B1: anti-deadlock escalation must be suppressed by escalation_suppress_on "
        "even when should_emit_anti_deadlock_escalation returns True"
    )

    orch_b2, mem_b2 = make_dev_orchestrator()
    rid_b2 = orch_b2.create_run("escalation_suppress_on")
    _append_fail_gate_row(mem_b2, rid_b2, "implementation.critique")
    _append_fail_gate_row(mem_b2, rid_b2, "test_writer.critique")
    with patch(
        "hermes_orchestrator.pipeline.load_escalate_after_cumulative_gate_failures",
        return_value=2,
    ):
        orch_b2._maybe_escalate_after_cumulative_gate_failures(rid_b2)  # noqa: SLF001
    assert _run_escalated_reasons(mem_b2, rid_b2) == [], (
        "B2: cumulative gate-failures escalation must be suppressed by "
        "escalation_suppress_on with 2 FAIL gates + threshold=2"
    )

    orch_b3, mem_b3 = make_dev_orchestrator()
    rid_b3_suppress = orch_b3.create_run("escalation_suppress_on")
    rid_b3_default = orch_b3.create_run("default")
    _append_finding_row(mem_b3, rid_b3_suppress)
    _append_finding_row(mem_b3, rid_b3_suppress)
    _append_finding_row(mem_b3, rid_b3_default)
    _append_finding_row(mem_b3, rid_b3_default)
    with patch(
        "hermes_orchestrator.pipeline.load_auto_escalate_after_cumulative_findings",
        return_value=2,
    ):
        orch_b3._maybe_auto_escalate(rid_b3_suppress)  # noqa: SLF001
        orch_b3._maybe_auto_escalate(rid_b3_default)  # noqa: SLF001
    assert _run_escalated_reasons(mem_b3, rid_b3_suppress) == [], (
        "B3 suppress: _maybe_auto_escalate must short-circuit on escalation_suppress_on"
    )
    assert _run_escalated_reasons(mem_b3, rid_b3_default) == ["cumulative_findings_threshold"], (
        "B3 control: _maybe_auto_escalate must emit exactly 1 "
        "cumulative_findings_threshold escalation on default workflow with 2 findings + "
        "threshold=2 (the first direct base test for this method)"
    )

    orch_b4, mem_b4 = make_dev_orchestrator()
    rid_b4 = orch_b4.create_run("escalation_suppress_on")
    _append_finding_row(mem_b4, rid_b4)
    _append_finding_row(mem_b4, rid_b4)
    with patch(
        "hermes_orchestrator.pipeline.load_notice_escalate_at_cumulative_findings",
        return_value=2,
    ):
        orch_b4._maybe_notice_escalate_findings(rid_b4)  # noqa: SLF001
    assert _run_escalated_reasons(mem_b4, rid_b4) == [], (
        "B4: notice-findings escalation must be suppressed by escalation_suppress_on "
        "with 2 findings + notice_threshold=2"
    )

    orch_b5, mem_b5 = make_dev_orchestrator()
    rid_b5 = orch_b5.create_run("escalation_suppress_on")
    with patch(
        "hermes_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
        return_value=True,
    ):
        orch_b5._maybe_escalate_verifier_failure_checkpoint(rid_b5)  # noqa: SLF001
    assert _run_escalated_reasons(mem_b5, rid_b5) == [], (
        "B5: verifier-checkpoint escalation must be suppressed by "
        "escalation_suppress_on even with first-verifier-failure policy on"
    )


def test_workflow_profile_from_run_created_rows_4_axis_contract() -> None:
    """Pin the helper at integrator_gate.py:78-86 directly (pure function).

    Axis C1 -- empty rows list -> ``None`` (loop never enters).
    Axis C2 -- rows with no ``run.created`` event_type -> ``None``
    (pins the ``event_type != "run.created"`` continue branch).
    Axis C3 -- single ``run.created`` -> returns
    ``payload.workflow_profile`` as a string.
    Axis C4 -- two ``run.created`` rows -> **FIRST** in iteration
    order wins (pins the early-return contract that callers like
    ``_workflow_suppresses_automatic_escalation`` depend on via
    ``list_run_events`` sorted by ``store_seq``).
    """
    assert workflow_profile_from_run_created_rows([]) is None

    rows_c2: list[dict[str, Any]] = [
        {"event_type": "stage.passed", "payload": {"stage_name": "x"}},
        {"event_type": "run.started", "payload": {"started_by": "y"}},
    ]
    assert workflow_profile_from_run_created_rows(rows_c2) is None, (
        "rows without any run.created entry must yield None "
        "(event_type filter at integrator_gate.py:81)"
    )

    rows_c3: list[dict[str, Any]] = [
        {"event_type": "run.created", "payload": {"workflow_profile": "agent_evaluator_on"}},
    ]
    assert workflow_profile_from_run_created_rows(rows_c3) == "agent_evaluator_on"

    rows_c4: list[dict[str, Any]] = [
        {"event_type": "run.created", "payload": {"workflow_profile": "default"}},
        {
            "event_type": "run.created",
            "payload": {"workflow_profile": "escalation_suppress_on"},
        },
    ]
    assert workflow_profile_from_run_created_rows(rows_c4) == "default", (
        "two run.created rows: FIRST in iteration order must win (early return); "
        "callers rely on list_run_events store_seq ordering upstream"
    )
