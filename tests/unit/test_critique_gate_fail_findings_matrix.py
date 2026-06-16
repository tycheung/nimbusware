from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    FindingCreatedEvent,
    FindingCreatedPayload,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    Severity,
    Verdict,
)
from nimbusware_env import find_repo_root
from nimbusware_orchestrator.llm_plan import (
    IMPLEMENTATION_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
)
from nimbusware_orchestrator.pipeline import RunOrchestrator, make_dev_orchestrator
from nimbusware_orchestrator.workflow_universal_critique import effective_universal_critique

if TYPE_CHECKING:
    from nimbusware_store.memory import InMemoryEventStore

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])

_FINDING_CREATED = "finding.created"

_ENV_ALL_ON = {
    "NIMBUSWARE_UNIVERSAL_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL": "1",
}

_BACKEND_WRITER_PLACEHOLDER = UUID("44444444-4444-4444-8444-444444444404")


def _append_critique_gate(
    mem: InMemoryEventStore,
    rid: UUID,
    stage_name: str,
    verdict: Verdict,
    *,
    failure_reason_code: str | None = None,
    failing_critics: list[UUID] | None = None,
    failing_finding_ids: list[UUID] | None = None,
) -> None:
    """Append one synthesized critique gate row for the stage.

    For FAIL verdicts, the GateDecisionEmittedPayload validator requires at
    least one of ``failing_critics`` / ``failing_finding_ids`` /
    non-empty ``failure_reason_code``; we inject a default
    ``failure_reason_code`` when the caller does not supply any of these to
    keep call-sites compact.
    """
    fc_list = failing_critics or []
    ff_list = failing_finding_ids or []
    code = failure_reason_code
    if verdict == Verdict.FAIL and not fc_list and not ff_list and not (code or "").strip():
        code = "llm_gate_fail"
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name=stage_name,
                verdict=verdict,
                failure_reason_code=code,
                failing_critics=fc_list,
                failing_finding_ids=ff_list,
            ),
        ),
    )


def _append_prior_critique_fail_finding(
    mem: InMemoryEventStore,
    rid: UUID,
    stage_name: str,
) -> None:
    """Append a synthesized prior FINDING_CREATED carrying the dedup metadata."""
    mem.append(
        FindingCreatedEvent(
            event_type=EventType.FINDING_CREATED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "critique_gate_fail_finding": True,
                "stage_name": stage_name,
            },
            payload=FindingCreatedPayload(
                finding_id=uuid4(),
                category="critique",
                owner_role=_BACKEND_WRITER_PLACEHOLDER,
                severity=Severity.LOW,
                source_artifact=f"critique_gate:{stage_name}",
                repro_steps=[],
                required_fixes=[],
            ),
        ),
    )


def _findings_for(mem: InMemoryEventStore, rid: UUID) -> list[dict[str, Any]]:
    return [r for r in mem.list_run_events(str(rid)) if r.get("event_type") == _FINDING_CREATED]


def _stage_names_of(findings: list[dict[str, Any]]) -> list[str | None]:
    return [(f.get("metadata") or {}).get("stage_name") for f in findings]


def test_maybe_emit_critique_gate_fail_findings_multi_stage_matrix_4_axis() -> None:
    expected_all = {
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    }

    with patch.dict(os.environ, _ENV_ALL_ON, clear=False):
        orch_a1, mem_a1 = make_dev_orchestrator()
        rid_a1 = orch_a1.create_run("default")
        _append_critique_gate(mem_a1, rid_a1, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
        _append_critique_gate(mem_a1, rid_a1, TEST_WRITER_CRITIQUE_STAGE, Verdict.FAIL)
        _append_critique_gate(mem_a1, rid_a1, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
        eff_a1 = effective_universal_critique(ROOT, "default")
        orch_a1._maybe_emit_critique_gate_fail_findings(rid_a1, eff_a1)  # noqa: SLF001
        findings_a1 = _findings_for(mem_a1, rid_a1)
        assert len(findings_a1) == 3, (
            "A1: all 3 enabled + all 3 FAIL must emit one finding per stage"
        )
        assert set(_stage_names_of(findings_a1)) == expected_all, (
            "A1: stage_name metadata must cover impl + tw + planner exactly"
        )

        orch_a2, mem_a2 = make_dev_orchestrator()
        rid_a2 = orch_a2.create_run("default")
        _append_critique_gate(mem_a2, rid_a2, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
        _append_critique_gate(mem_a2, rid_a2, TEST_WRITER_CRITIQUE_STAGE, Verdict.PASS)
        _append_critique_gate(mem_a2, rid_a2, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
        eff_a2 = effective_universal_critique(ROOT, "default")
        orch_a2._maybe_emit_critique_gate_fail_findings(rid_a2, eff_a2)  # noqa: SLF001
        findings_a2 = _findings_for(mem_a2, rid_a2)
        assert len(findings_a2) == 2
        assert set(_stage_names_of(findings_a2)) == {
            IMPLEMENTATION_CRITIQUE_STAGE,
            PLANNER_CRITIQUE_STAGE,
        }, "A2: tw PASS verdict must be skipped via the verdict guard"

        orch_a3, mem_a3 = make_dev_orchestrator()
        rid_a3 = orch_a3.create_run("default")
        _append_critique_gate(mem_a3, rid_a3, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
        eff_a3 = effective_universal_critique(ROOT, "default")
        orch_a3._maybe_emit_critique_gate_fail_findings(rid_a3, eff_a3)  # noqa: SLF001
        findings_a3 = _findings_for(mem_a3, rid_a3)
        assert len(findings_a3) == 1
        assert _stage_names_of(findings_a3) == [IMPLEMENTATION_CRITIQUE_STAGE], (
            "A3: only the stage with a gate row must emit"
        )

        orch_a4, mem_a4 = make_dev_orchestrator()
        rid_a4 = orch_a4.create_run("default")
        _append_prior_critique_fail_finding(mem_a4, rid_a4, IMPLEMENTATION_CRITIQUE_STAGE)
        _append_critique_gate(mem_a4, rid_a4, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
        _append_critique_gate(mem_a4, rid_a4, TEST_WRITER_CRITIQUE_STAGE, Verdict.FAIL)
        _append_critique_gate(mem_a4, rid_a4, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
        eff_a4 = effective_universal_critique(ROOT, "default")
        orch_a4._maybe_emit_critique_gate_fail_findings(rid_a4, eff_a4)  # noqa: SLF001
        findings_a4 = _findings_for(mem_a4, rid_a4)
        assert len(findings_a4) == 3, (
            "A4: 1 prior impl + 2 new (tw + planner); total 3 finding rows"
        )
        new_stages_a4 = [
            (f.get("metadata") or {}).get("stage_name")
            for f in findings_a4
            if (f.get("payload") or {}).get("source_artifact")
            != (f"critique_gate:{IMPLEMENTATION_CRITIQUE_STAGE}")
            or (f.get("payload") or {}).get("category") == "critique"
        ]
        all_stages_a4 = set(_stage_names_of(findings_a4))
        assert all_stages_a4 == expected_all, (
            "A4: per-stage isolation -- impl prior + tw + planner new "
            "yields a set covering all 3 stages"
        )
        assert new_stages_a4.count(IMPLEMENTATION_CRITIQUE_STAGE) == 1, (
            "A4: impl was silently skipped on the call; only the prior "
            "synthesized impl row should match"
        )


def test_maybe_emit_critique_gate_fail_findings_skip_branches_4_axis() -> None:
    orch_b1, mem_b1 = make_dev_orchestrator()
    rid_b1 = orch_b1.create_run("default")
    _append_critique_gate(mem_b1, rid_b1, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
    _append_critique_gate(mem_b1, rid_b1, TEST_WRITER_CRITIQUE_STAGE, Verdict.FAIL)
    _append_critique_gate(mem_b1, rid_b1, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
    eff_b1 = effective_universal_critique(ROOT, "default")
    orch_b1._maybe_emit_critique_gate_fail_findings(rid_b1, eff_b1)  # noqa: SLF001
    assert _findings_for(mem_b1, rid_b1) == [], (
        "B1: default workflow disables all 3 stages -> 0 findings"
    )

    with patch.dict(
        os.environ,
        {"NIMBUSWARE_UNIVERSAL_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL": "1"},
        clear=False,
    ):
        orch_b2, mem_b2 = make_dev_orchestrator()
        rid_b2 = orch_b2.create_run("default")
        _append_prior_critique_fail_finding(mem_b2, rid_b2, IMPLEMENTATION_CRITIQUE_STAGE)
        _append_critique_gate(mem_b2, rid_b2, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
        eff_b2 = effective_universal_critique(ROOT, "default")
        orch_b2._maybe_emit_critique_gate_fail_findings(rid_b2, eff_b2)  # noqa: SLF001
        assert len(_findings_for(mem_b2, rid_b2)) == 1, (
            "B2: prior impl finding short-circuits the already-emitted guard "
            "(only the synthesized prior row remains)"
        )

        orch_b3, mem_b3 = make_dev_orchestrator()
        rid_b3 = orch_b3.create_run("default")
        eff_b3 = effective_universal_critique(ROOT, "default")
        orch_b3._maybe_emit_critique_gate_fail_findings(rid_b3, eff_b3)  # noqa: SLF001
        assert _findings_for(mem_b3, rid_b3) == [], (
            "B3: enabled but no gate row -> not gate_pl arm short-circuits"
        )

        orch_b4, mem_b4 = make_dev_orchestrator()
        rid_b4 = orch_b4.create_run("default")
        _append_critique_gate(
            mem_b4,
            rid_b4,
            IMPLEMENTATION_CRITIQUE_STAGE,
            Verdict.NEEDS_INFO,
        )
        eff_b4 = effective_universal_critique(ROOT, "default")
        orch_b4._maybe_emit_critique_gate_fail_findings(rid_b4, eff_b4)  # noqa: SLF001
        assert _findings_for(mem_b4, rid_b4) == [], (
            "B4: NEEDS_INFO verdict short-circuits the verdict guard"
        )


def test_maybe_emit_critique_gate_fail_findings_payload_shape_4_axis() -> None:
    role_for_stage = {
        IMPLEMENTATION_CRITIQUE_STAGE: "backend_writer",
        TEST_WRITER_CRITIQUE_STAGE: "test_writer",
        PLANNER_CRITIQUE_STAGE: "planner",
    }

    with patch.dict(os.environ, _ENV_ALL_ON, clear=False):
        orch_c, mem_c = make_dev_orchestrator()
        rid_c = orch_c.create_run("default")
        _append_critique_gate(mem_c, rid_c, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
        _append_critique_gate(mem_c, rid_c, TEST_WRITER_CRITIQUE_STAGE, Verdict.FAIL)
        _append_critique_gate(mem_c, rid_c, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
        eff_c = effective_universal_critique(ROOT, "default")
        orch_c._maybe_emit_critique_gate_fail_findings(rid_c, eff_c)  # noqa: SLF001
        findings_c = _findings_for(mem_c, rid_c)
        assert len(findings_c) == 3
        by_stage = {(f.get("metadata") or {}).get("stage_name"): f for f in findings_c}

        for stage_name in (
            IMPLEMENTATION_CRITIQUE_STAGE,
            TEST_WRITER_CRITIQUE_STAGE,
            PLANNER_CRITIQUE_STAGE,
        ):
            f = by_stage[stage_name]
            pl = f.get("payload") or {}
            assert pl.get("source_artifact") == f"critique_gate:{stage_name}", (
                f"C1: source_artifact mismatch for {stage_name}"
            )
            expected_owner = orch_c._registry.resolve(role_for_stage[stage_name])  # noqa: SLF001
            assert UUID(str(pl.get("owner_role"))) == expected_owner, (
                f"C2: owner_role for {stage_name} must resolve to "
                f"{role_for_stage[stage_name]!r} registry UUID"
            )

        orch_c3, mem_c3 = make_dev_orchestrator()
        rid_c3 = orch_c3.create_run("default")
        fc_ids = [uuid4(), uuid4()]
        ff_ids = [uuid4(), uuid4(), uuid4()]
        _append_critique_gate(
            mem_c3,
            rid_c3,
            IMPLEMENTATION_CRITIQUE_STAGE,
            Verdict.FAIL,
            failure_reason_code="custom_code",
            failing_critics=fc_ids,
            failing_finding_ids=ff_ids,
        )
        eff_c3 = effective_universal_critique(ROOT, "default")
        orch_c3._maybe_emit_critique_gate_fail_findings(rid_c3, eff_c3)  # noqa: SLF001
        findings_c3 = _findings_for(mem_c3, rid_c3)
        assert len(findings_c3) == 1
        repro = (findings_c3[0].get("payload") or {}).get("repro_steps")
        assert repro == [
            f"stage={IMPLEMENTATION_CRITIQUE_STAGE}",
            "verdict=FAIL",
            "failure_reason_code=custom_code",
            "failing_critics=2 critic(s)",
            "failing_finding_ids=3 id(s)",
        ], "C3: repro_steps must propagate gate fields in strict 5-line order"

        for f in findings_c:
            pl = f.get("payload") or {}
            meta = f.get("metadata") or {}
            assert (pl.get("category") or "").lower() == "critique", "C4: category invariant"
            assert pl.get("severity") == Severity.LOW.value, "C4: severity invariant must be LOW"
            assert pl.get("required_fixes") == [], "C4: required_fixes invariant must be empty list"
            assert meta.get("critique_gate_fail_finding") is True, "C4: metadata flag invariant"


def test_critique_gate_fail_pure_helpers_direct_contract_4_axis() -> None:
    is_fail = RunOrchestrator._critique_gate_verdict_is_fail  # noqa: SLF001
    assert is_fail({"verdict": Verdict.FAIL}) is True
    assert is_fail({"verdict": "FAIL"}) is True
    assert is_fail({"verdict": "fail"}) is True
    assert is_fail({"verdict": "  Fail  "}) is True
    assert is_fail({"verdict": "PASS"}) is False
    assert is_fail({}) is False, "D1: missing key must return False"

    last_for = RunOrchestrator._last_critique_gate_payload_for_stage  # noqa: SLF001
    assert last_for([], IMPLEMENTATION_CRITIQUE_STAGE) is None, "D2: empty rows"
    rows_no_gate: list[dict[str, Any]] = [
        {"event_type": "run.started", "payload": {"started_by": "x"}},
        {"event_type": "finding.created", "payload": {}},
    ]
    assert last_for(rows_no_gate, IMPLEMENTATION_CRITIQUE_STAGE) is None, (
        "D2: rows present but no gate.decision.emitted -> None"
    )
    rows_wrong_stage: list[dict[str, Any]] = [
        {
            "event_type": EventType.GATE_DECISION_EMITTED.value,
            "payload": {"stage_name": "planner.critique", "verdict": "PASS"},
        },
    ]
    assert last_for(rows_wrong_stage, IMPLEMENTATION_CRITIQUE_STAGE) is None, (
        "D2: stage filter rejects gate rows for other stages"
    )
    rows_multi: list[dict[str, Any]] = [
        {
            "event_type": EventType.GATE_DECISION_EMITTED.value,
            "payload": {
                "stage_name": IMPLEMENTATION_CRITIQUE_STAGE,
                "verdict": "PASS",
                "marker": "first",
            },
        },
        {
            "event_type": EventType.GATE_DECISION_EMITTED.value,
            "payload": {
                "stage_name": IMPLEMENTATION_CRITIQUE_STAGE,
                "verdict": "FAIL",
                "marker": "last",
            },
        },
    ]
    last_payload = last_for(rows_multi, IMPLEMENTATION_CRITIQUE_STAGE)
    assert last_payload is not None and last_payload.get("marker") == "last", (
        "D2: with multiple gates for the same stage, LAST in iteration "
        "order wins (pins the no-early-break contract)"
    )

    already = RunOrchestrator._critique_gate_fail_finding_already_emitted  # noqa: SLF001
    assert already([], IMPLEMENTATION_CRITIQUE_STAGE) is False, "D3: empty"
    rows_no_meta: list[dict[str, Any]] = [
        {"event_type": EventType.FINDING_CREATED.value, "metadata": {}},
    ]
    assert already(rows_no_meta, IMPLEMENTATION_CRITIQUE_STAGE) is False, (
        "D3: finding without critique_gate_fail_finding flag -> False"
    )
    rows_stage_mismatch: list[dict[str, Any]] = [
        {
            "event_type": EventType.FINDING_CREATED.value,
            "metadata": {
                "critique_gate_fail_finding": True,
                "stage_name": TEST_WRITER_CRITIQUE_STAGE,
            },
        },
    ]
    assert already(rows_stage_mismatch, IMPLEMENTATION_CRITIQUE_STAGE) is False, (
        "D3: stage_name mismatch -> False (per-stage isolation; the helper "
        "A4 pin proves this end-to-end)"
    )
    rows_hit: list[dict[str, Any]] = [
        {
            "event_type": EventType.FINDING_CREATED.value,
            "metadata": {
                "critique_gate_fail_finding": True,
                "stage_name": IMPLEMENTATION_CRITIQUE_STAGE,
            },
        },
    ]
    assert already(rows_hit, IMPLEMENTATION_CRITIQUE_STAGE) is True

    orch_d, _ = make_dev_orchestrator()
    repro = orch_d._repro_steps_from_critique_gate  # noqa: SLF001
    assert repro({"stage_name": "x", "verdict": "FAIL"}) == [
        "stage=x",
        "verdict=FAIL",
    ], "D4: minimal 2-line composition"
    fc = [uuid4(), uuid4()]
    ff = [uuid4()]
    assert repro(
        {
            "stage_name": "implementation.critique",
            "verdict": "FAIL",
            "failure_reason_code": "code_x",
            "failing_critics": fc,
            "failing_finding_ids": ff,
        },
    ) == [
        "stage=implementation.critique",
        "verdict=FAIL",
        "failure_reason_code=code_x",
        "failing_critics=2 critic(s)",
        "failing_finding_ids=1 id(s)",
    ], "D4: full 5-line strict-order composition"
    assert repro(
        {
            "stage_name": "x",
            "verdict": "FAIL",
            "failure_reason_code": "  spaced  ",
        },
    ) == [
        "stage=x",
        "verdict=FAIL",
        "failure_reason_code=spaced",
    ], "D4: failure_reason_code must be .strip()-ed before composition"
    assert repro(
        {
            "stage_name": "x",
            "verdict": "FAIL",
            "failing_critics": "not-a-list",
            "failing_finding_ids": [],
        },
    ) == [
        "stage=x",
        "verdict=FAIL",
    ], (
        "D4: non-list failing_critics and empty failing_finding_ids "
        "are silently ignored (isinstance + truthy guards)"
    )
