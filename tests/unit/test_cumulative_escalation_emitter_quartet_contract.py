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
    RunEscalatedEvent,
    RunEscalatedPayload,
    Severity,
    StageFailedEvent,
    StageFailedPayload,
    StagePassedEvent,
    StagePassedPayload,
    Verdict,
)
from hermes_orchestrator.pipeline import make_dev_orchestrator

if TYPE_CHECKING:
    from hermes_store.memory import InMemoryEventStore


_BACKEND_WRITER = UUID("44444444-4444-4444-8444-444444444404")


def _append_stage_failed(mem: InMemoryEventStore, run_id: UUID, name: str) -> None:
    """Append one synthetic ``stage.failed`` row."""
    mem.append(
        StageFailedEvent(
            event_type=EventType.STAGE_FAILED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageFailedPayload(stage_name=name, reason_code="x", message="m"),
        ),
    )


def _append_stage_passed(mem: InMemoryEventStore, run_id: UUID, name: str) -> None:
    """Append one synthetic ``stage.passed`` row (count-filter foil)."""
    mem.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StagePassedPayload(stage_name=name, duration_ms=0),
        ),
    )


def _append_fail_gate(mem: InMemoryEventStore, run_id: UUID, stage: str) -> None:
    """Append one FAIL ``gate.decision.emitted`` row; FAIL requires a signal."""
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name=stage,
                verdict=Verdict.FAIL,
                failure_reason_code="fo102_synthetic_fail",
            ),
        ),
    )


def _append_pass_gate(mem: InMemoryEventStore, run_id: UUID, stage: str) -> None:
    """Append one PASS ``gate.decision.emitted`` row (Part B count-filter foil)."""
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name=stage,
                verdict=Verdict.PASS,
            ),
        ),
    )


def _append_finding(mem: InMemoryEventStore, run_id: UUID) -> None:
    """Append one LOW-severity ``finding.created`` row (default strictness allows LOW + no fix)."""
    mem.append(
        FindingCreatedEvent(
            event_type=EventType.FINDING_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=FindingCreatedPayload(
                finding_id=uuid4(),
                category="fo102_synthetic",
                owner_role=_BACKEND_WRITER,
                severity=Severity.LOW,
                source_artifact="fo102",
                repro_steps=[],
                required_fixes=[],
            ),
        ),
    )


def _append_escalation(mem: InMemoryEventStore, run_id: UUID, reason_code: str) -> None:
    """Append one pre-existing ``run.escalated`` row with the chosen reason_code."""
    mem.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="system:fo102-seed",
                reason_code=reason_code,
                notes="pre-existing seed",
            ),
        ),
    )


def _escalation_rows(mem: InMemoryEventStore, run_id: UUID) -> list[dict[str, Any]]:
    """Return RUN_ESCALATED rows for the run in order."""
    return [
        r
        for r in mem.list_run_events(str(run_id))
        if r["event_type"] == EventType.RUN_ESCALATED.value
    ]


def test_cumulative_stage_failures_emitter_5_axis() -> None:
    """Pin _maybe_escalate_after_cumulative_stage_failures at pipeline.py:1283-1311.

    Coverage delta vs existing test_cumulative_stage_failure_escalation.py:
    the existing 3 axes (dedup-happy / suppress / parametrized below-threshold)
    do NOT pin threshold-None, the exact notes string, or the count-filter
    asymmetry. fo102's A1/A4/A5 close those.
    """
    orch_a1, mem_a1 = make_dev_orchestrator()
    rid_a1 = orch_a1.create_run("default")
    _append_stage_failed(mem_a1, rid_a1, "s1")
    _append_stage_failed(mem_a1, rid_a1, "s2")
    with patch(
        "hermes_orchestrator.pipeline.load_escalate_after_cumulative_stage_failures",
        return_value=None,
    ):
        orch_a1._maybe_escalate_after_cumulative_stage_failures(rid_a1)  # noqa: SLF001
    assert _escalation_rows(mem_a1, rid_a1) == [], (
        "A1: threshold=None -> early-return BEFORE row scan; 2 STAGE_FAILED "
        "rows that would otherwise hit threshold=2 must produce zero escalations"
    )

    orch_a2, mem_a2 = make_dev_orchestrator()
    rid_a2 = orch_a2.create_run("default")
    _append_stage_failed(mem_a2, rid_a2, "s1")
    _append_stage_failed(mem_a2, rid_a2, "s2")
    _append_escalation(mem_a2, rid_a2, "cumulative_stage_failures")
    with patch(
        "hermes_orchestrator.pipeline.load_escalate_after_cumulative_stage_failures",
        return_value=2,
    ):
        orch_a2._maybe_escalate_after_cumulative_stage_failures(rid_a2)  # noqa: SLF001
    rows_a2 = _escalation_rows(mem_a2, rid_a2)
    assert len(rows_a2) == 1, (
        "A2: per-reason-code dedup -- pre-existing cumulative_stage_failures "
        "RUN_ESCALATED row short-circuits; no second emission"
    )

    orch_a3, mem_a3 = make_dev_orchestrator()
    rid_a3 = orch_a3.create_run("default")
    _append_stage_failed(mem_a3, rid_a3, "s1")
    with patch(
        "hermes_orchestrator.pipeline.load_escalate_after_cumulative_stage_failures",
        return_value=2,
    ):
        orch_a3._maybe_escalate_after_cumulative_stage_failures(rid_a3)  # noqa: SLF001
    assert _escalation_rows(mem_a3, rid_a3) == [], (
        "A3: under threshold (n_failed=1 < threshold=2) -> early-return; "
        "pins `if n_failed < threshold: return`"
    )

    orch_a4, mem_a4 = make_dev_orchestrator()
    rid_a4 = orch_a4.create_run("default")
    _append_stage_failed(mem_a4, rid_a4, "s1")
    _append_stage_failed(mem_a4, rid_a4, "s2")
    with patch(
        "hermes_orchestrator.pipeline.load_escalate_after_cumulative_stage_failures",
        return_value=2,
    ):
        orch_a4._maybe_escalate_after_cumulative_stage_failures(rid_a4)  # noqa: SLF001
    rows_a4 = _escalation_rows(mem_a4, rid_a4)
    assert len(rows_a4) == 1, "A4: hit threshold -> exactly 1 emission"
    pl_a4 = rows_a4[0].get("payload") or {}
    assert pl_a4.get("reason_code") == "cumulative_stage_failures", (
        "A4: emitted reason_code matches the helper's literal"
    )
    assert pl_a4.get("notes") == "threshold=2 cumulative_stage_failed=2", (
        "A4: notes string is exact f-string output "
        "`f'threshold={threshold} cumulative_stage_failed={n_failed}'` "
        "(pins the literal format -- rename-resistant guard)"
    )

    orch_a5, mem_a5 = make_dev_orchestrator()
    rid_a5 = orch_a5.create_run("default")
    _append_stage_failed(mem_a5, rid_a5, "s1")
    _append_stage_failed(mem_a5, rid_a5, "s2")
    _append_stage_passed(mem_a5, rid_a5, "p1")
    _append_finding(mem_a5, rid_a5)
    with patch(
        "hermes_orchestrator.pipeline.load_escalate_after_cumulative_stage_failures",
        return_value=2,
    ):
        orch_a5._maybe_escalate_after_cumulative_stage_failures(rid_a5)  # noqa: SLF001
    rows_a5 = _escalation_rows(mem_a5, rid_a5)
    assert len(rows_a5) == 1, "A5: hit threshold -> exactly 1 emission"
    pl_a5 = rows_a5[0].get("payload") or {}
    assert pl_a5.get("notes") == "threshold=2 cumulative_stage_failed=2", (
        "A5: count-filter -- notes ends with `cumulative_stage_failed=2` "
        "(NOT 3 or 4); pins that STAGE_PASSED and FINDING_CREATED rows are "
        "NOT counted (only STAGE_FAILED matches at pipeline.py:1296)"
    )


def test_cumulative_gate_failures_emitter_5_axis() -> None:
    """Pin _maybe_escalate_after_cumulative_gate_failures at pipeline.py:1313-1347.

    Coverage delta vs existing test_gate_failure_escalation.py (1-axis happy
    + dedup): fo102 adds threshold-None, below-threshold, notes-format, and
    the PASS-gate-filter axis (critical inner verdict==FAIL.value guard).
    """
    orch_b1, mem_b1 = make_dev_orchestrator()
    rid_b1 = orch_b1.create_run("default")
    for i in range(3):
        _append_fail_gate(mem_b1, rid_b1, f"g{i}")
    with patch(
        "hermes_orchestrator.pipeline.load_escalate_after_cumulative_gate_failures",
        return_value=None,
    ):
        orch_b1._maybe_escalate_after_cumulative_gate_failures(rid_b1)  # noqa: SLF001
    assert _escalation_rows(mem_b1, rid_b1) == [], (
        "B1: threshold=None -> early-return BEFORE row scan; 3 FAIL gates "
        "that would otherwise hit threshold must produce zero escalations"
    )

    orch_b2, mem_b2 = make_dev_orchestrator()
    rid_b2 = orch_b2.create_run("default")
    _append_fail_gate(mem_b2, rid_b2, "g1")
    _append_fail_gate(mem_b2, rid_b2, "g2")
    _append_escalation(mem_b2, rid_b2, "cumulative_gate_failures")
    with patch(
        "hermes_orchestrator.pipeline.load_escalate_after_cumulative_gate_failures",
        return_value=2,
    ):
        orch_b2._maybe_escalate_after_cumulative_gate_failures(rid_b2)  # noqa: SLF001
    assert len(_escalation_rows(mem_b2, rid_b2)) == 1, (
        "B2: per-reason-code dedup -- pre-existing cumulative_gate_failures "
        "RUN_ESCALATED short-circuits; no second emission"
    )

    orch_b3, mem_b3 = make_dev_orchestrator()
    rid_b3 = orch_b3.create_run("default")
    _append_fail_gate(mem_b3, rid_b3, "g1")
    _append_fail_gate(mem_b3, rid_b3, "g2")
    with patch(
        "hermes_orchestrator.pipeline.load_escalate_after_cumulative_gate_failures",
        return_value=3,
    ):
        orch_b3._maybe_escalate_after_cumulative_gate_failures(rid_b3)  # noqa: SLF001
    assert _escalation_rows(mem_b3, rid_b3) == [], (
        "B3: under threshold (n_gate_fail=2 < threshold=3) -> early-return"
    )

    orch_b4, mem_b4 = make_dev_orchestrator()
    rid_b4 = orch_b4.create_run("default")
    _append_fail_gate(mem_b4, rid_b4, "g1")
    _append_fail_gate(mem_b4, rid_b4, "g2")
    with patch(
        "hermes_orchestrator.pipeline.load_escalate_after_cumulative_gate_failures",
        return_value=2,
    ):
        orch_b4._maybe_escalate_after_cumulative_gate_failures(rid_b4)  # noqa: SLF001
    rows_b4 = _escalation_rows(mem_b4, rid_b4)
    assert len(rows_b4) == 1, "B4: hit threshold -> exactly 1 emission"
    pl_b4 = rows_b4[0].get("payload") or {}
    assert pl_b4.get("reason_code") == "cumulative_gate_failures"
    assert pl_b4.get("notes") == "threshold=2 cumulative_gate_failed=2", (
        "B4: notes string is exact f-string output "
        "`f'threshold={threshold} cumulative_gate_failed={n_gate_fail}'`"
    )

    orch_b5, mem_b5 = make_dev_orchestrator()
    rid_b5 = orch_b5.create_run("default")
    _append_pass_gate(mem_b5, rid_b5, "g1")
    _append_pass_gate(mem_b5, rid_b5, "g2")
    _append_fail_gate(mem_b5, rid_b5, "g3")
    with patch(
        "hermes_orchestrator.pipeline.load_escalate_after_cumulative_gate_failures",
        return_value=2,
    ):
        orch_b5._maybe_escalate_after_cumulative_gate_failures(rid_b5)  # noqa: SLF001
    assert _escalation_rows(mem_b5, rid_b5) == [], (
        "B5: count-filter -- 2 PASS gates + 1 FAIL gate; n_gate_fail=1 < "
        "threshold=2 -> no emission. CRITICAL: pins the inner "
        "`if pl.get('verdict') == Verdict.FAIL.value:` guard at "
        "pipeline.py:1331 -- WITHOUT it, total gate count would be 3 and "
        "threshold would hit (false positive)"
    )


def test_auto_escalate_findings_emitter_5_axis() -> None:
    """Pin _maybe_auto_escalate at pipeline.py:1349-1373.

    Coverage delta vs existing: fo88's B3 added 1 control axis (this method's
    first direct test). fo102 closes the asymmetric ANY-RUN_ESCALATED dedup
    (different from Parts A/B/D's per-reason-code dedup), threshold-None,
    below-threshold, notes-format, and the count-filter axes.
    """
    orch_c1, mem_c1 = make_dev_orchestrator()
    rid_c1 = orch_c1.create_run("default")
    for _ in range(3):
        _append_finding(mem_c1, rid_c1)
    with patch(
        "hermes_orchestrator.pipeline.load_auto_escalate_after_cumulative_findings",
        return_value=None,
    ):
        orch_c1._maybe_auto_escalate(rid_c1)  # noqa: SLF001
    assert _escalation_rows(mem_c1, rid_c1) == [], (
        "C1: threshold=None -> early-return BEFORE row scan; 3 findings that "
        "would otherwise hit threshold must produce zero escalations"
    )

    orch_c2, mem_c2 = make_dev_orchestrator()
    rid_c2 = orch_c2.create_run("default")
    _append_finding(mem_c2, rid_c2)
    _append_finding(mem_c2, rid_c2)
    _append_escalation(mem_c2, rid_c2, "anti_deadlock_insufficient_progress")
    with patch(
        "hermes_orchestrator.pipeline.load_auto_escalate_after_cumulative_findings",
        return_value=2,
    ):
        orch_c2._maybe_auto_escalate(rid_c2)  # noqa: SLF001
    rows_c2 = _escalation_rows(mem_c2, rid_c2)
    assert len(rows_c2) == 1, (
        "C2: ANY-RUN_ESCALATED dedup -- pre-existing RUN_ESCALATED with "
        "an UNRELATED reason_code (anti_deadlock_insufficient_progress) "
        "still short-circuits this emitter; NO second emission. "
        "CRITICAL: pins the asymmetric guard at pipeline.py:1356 "
        "`any(r['event_type'] == RUN_ESCALATED.value for r in rows)` "
        "which is reason-code-AGNOSTIC, unlike Parts A/B/D which only "
        "dedup on their own reason_code"
    )
    assert (rows_c2[0].get("payload") or {}).get("reason_code") == (
        "anti_deadlock_insufficient_progress"
    ), "C2 cross-cut: the surviving row is the pre-seeded one, not auto-emit"

    orch_c3, mem_c3 = make_dev_orchestrator()
    rid_c3 = orch_c3.create_run("default")
    _append_finding(mem_c3, rid_c3)
    _append_finding(mem_c3, rid_c3)
    with patch(
        "hermes_orchestrator.pipeline.load_auto_escalate_after_cumulative_findings",
        return_value=3,
    ):
        orch_c3._maybe_auto_escalate(rid_c3)  # noqa: SLF001
    assert _escalation_rows(mem_c3, rid_c3) == [], (
        "C3: under threshold (n_findings=2 < threshold=3) -> early-return"
    )

    orch_c4, mem_c4 = make_dev_orchestrator()
    rid_c4 = orch_c4.create_run("default")
    _append_finding(mem_c4, rid_c4)
    _append_finding(mem_c4, rid_c4)
    with patch(
        "hermes_orchestrator.pipeline.load_auto_escalate_after_cumulative_findings",
        return_value=2,
    ):
        orch_c4._maybe_auto_escalate(rid_c4)  # noqa: SLF001
    rows_c4 = _escalation_rows(mem_c4, rid_c4)
    assert len(rows_c4) == 1, "C4: hit threshold -> exactly 1 emission"
    pl_c4 = rows_c4[0].get("payload") or {}
    assert pl_c4.get("reason_code") == "cumulative_findings_threshold"
    assert pl_c4.get("notes") == "threshold=2 cumulative_findings=2", (
        "C4: notes string is exact f-string output "
        "`f'threshold={threshold} cumulative_findings={n_findings}'`"
    )

    orch_c5, mem_c5 = make_dev_orchestrator()
    rid_c5 = orch_c5.create_run("default")
    _append_finding(mem_c5, rid_c5)
    _append_finding(mem_c5, rid_c5)
    _append_stage_failed(mem_c5, rid_c5, "s1")
    _append_fail_gate(mem_c5, rid_c5, "g1")
    with patch(
        "hermes_orchestrator.pipeline.load_auto_escalate_after_cumulative_findings",
        return_value=2,
    ):
        orch_c5._maybe_auto_escalate(rid_c5)  # noqa: SLF001
    rows_c5 = _escalation_rows(mem_c5, rid_c5)
    assert len(rows_c5) == 1, "C5: hit threshold -> exactly 1 emission"
    pl_c5 = rows_c5[0].get("payload") or {}
    assert pl_c5.get("notes") == "threshold=2 cumulative_findings=2", (
        "C5: count-filter -- notes ends with `cumulative_findings=2` "
        "(NOT 3 or 4); pins that STAGE_FAILED and GATE_DECISION_EMITTED rows "
        "are NOT counted (only FINDING_CREATED matches at pipeline.py:1358)"
    )


def test_notice_escalate_findings_emitter_5_axis() -> None:
    """Pin _maybe_notice_escalate_findings at pipeline.py:1375-1403.

    Coverage delta vs existing: only fo88's B4 suppress axis exists; ALL
    happy-path / threshold / dedup / notes / cross-cut axes are unpinned today.
    D4 also pins the asymmetric `notice_threshold=` prefix vs the canonical
    `threshold=` used by Parts A/B/C; D5 pins the one-directional dedup
    interaction with Part C.
    """
    orch_d1, mem_d1 = make_dev_orchestrator()
    rid_d1 = orch_d1.create_run("default")
    for _ in range(3):
        _append_finding(mem_d1, rid_d1)
    with patch(
        "hermes_orchestrator.pipeline.load_notice_escalate_at_cumulative_findings",
        return_value=None,
    ):
        orch_d1._maybe_notice_escalate_findings(rid_d1)  # noqa: SLF001
    assert _escalation_rows(mem_d1, rid_d1) == [], (
        "D1: threshold=None -> early-return BEFORE row scan; 3 findings that "
        "would otherwise hit notice_threshold must produce zero escalations"
    )

    orch_d2, mem_d2 = make_dev_orchestrator()
    rid_d2 = orch_d2.create_run("default")
    _append_finding(mem_d2, rid_d2)
    _append_finding(mem_d2, rid_d2)
    _append_escalation(mem_d2, rid_d2, "cumulative_findings_notice")
    with patch(
        "hermes_orchestrator.pipeline.load_notice_escalate_at_cumulative_findings",
        return_value=2,
    ):
        orch_d2._maybe_notice_escalate_findings(rid_d2)  # noqa: SLF001
    assert len(_escalation_rows(mem_d2, rid_d2)) == 1, (
        "D2: per-reason-code dedup -- pre-existing cumulative_findings_notice "
        "RUN_ESCALATED short-circuits; no second emission. Contrast with "
        "Part C2 where ANY reason_code blocks; here only the matching reason"
    )

    orch_d3, mem_d3 = make_dev_orchestrator()
    rid_d3 = orch_d3.create_run("default")
    _append_finding(mem_d3, rid_d3)
    _append_finding(mem_d3, rid_d3)
    with patch(
        "hermes_orchestrator.pipeline.load_notice_escalate_at_cumulative_findings",
        return_value=3,
    ):
        orch_d3._maybe_notice_escalate_findings(rid_d3)  # noqa: SLF001
    assert _escalation_rows(mem_d3, rid_d3) == [], (
        "D3: under threshold (n_findings=2 < threshold=3) -> early-return"
    )

    orch_d4, mem_d4 = make_dev_orchestrator()
    rid_d4 = orch_d4.create_run("default")
    _append_finding(mem_d4, rid_d4)
    _append_finding(mem_d4, rid_d4)
    with patch(
        "hermes_orchestrator.pipeline.load_notice_escalate_at_cumulative_findings",
        return_value=2,
    ):
        orch_d4._maybe_notice_escalate_findings(rid_d4)  # noqa: SLF001
    rows_d4 = _escalation_rows(mem_d4, rid_d4)
    assert len(rows_d4) == 1, "D4: hit threshold -> exactly 1 emission"
    pl_d4 = rows_d4[0].get("payload") or {}
    assert pl_d4.get("reason_code") == "cumulative_findings_notice"
    assert pl_d4.get("notes") == "notice_threshold=2 cumulative_findings=2", (
        "D4: notes string uses ASYMMETRIC `notice_threshold=` prefix "
        "(vs Parts A/B/C which use `threshold=`); CRITICAL pin -- this is "
        "the one place in the quartet where the notes format diverges from "
        "the canonical pattern, invisible if you skim past pipeline.py:1400"
    )

    orch_d5, mem_d5 = make_dev_orchestrator()
    rid_d5 = orch_d5.create_run("default")
    _append_finding(mem_d5, rid_d5)
    _append_finding(mem_d5, rid_d5)
    with (
        patch(
            "hermes_orchestrator.pipeline.load_notice_escalate_at_cumulative_findings",
            return_value=2,
        ),
        patch(
            "hermes_orchestrator.pipeline.load_auto_escalate_after_cumulative_findings",
            return_value=2,
        ),
    ):
        orch_d5._maybe_notice_escalate_findings(rid_d5)  # noqa: SLF001
        rows_after_notice = _escalation_rows(mem_d5, rid_d5)
        assert len(rows_after_notice) == 1, "D5: notice emits first -> 1 row"
        assert (rows_after_notice[0].get("payload") or {}).get("reason_code") == (
            "cumulative_findings_notice"
        ), "D5: first emission is from notice helper"

        orch_d5._maybe_auto_escalate(rid_d5)  # noqa: SLF001
    rows_after_auto = _escalation_rows(mem_d5, rid_d5)
    assert len(rows_after_auto) == 1, (
        "D5 cross-cut: after notice emits, _maybe_auto_escalate's "
        "ANY-RUN_ESCALATED dedup (pinned in C2) short-circuits -> still 1 row. "
        "Pins the ONE-DIRECTIONAL interaction: D's per-reason dedup does NOT "
        "preemptively block C, but C's any-escalated dedup DOES block its "
        "own emission AFTER D emitted; sharpest behavioral pin in the quartet"
    )
    assert (rows_after_auto[0].get("payload") or {}).get("reason_code") == (
        "cumulative_findings_notice"
    ), "D5 cross-cut: surviving row is still the notice one (no auto override)"
