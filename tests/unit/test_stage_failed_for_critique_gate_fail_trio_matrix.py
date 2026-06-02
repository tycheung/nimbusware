"""_maybe_emit_stage_failed_for_*_critique_gate_fail`` trio direct contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import patch
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    StageFailedEvent,
    StageFailedPayload,
    Verdict,
)
from hermes_orchestrator.llm_plan import (
    IMPLEMENTATION_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
)
from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.workflow_universal_critique import EffectiveUniversalCritique

if TYPE_CHECKING:
    from hermes_store.memory import InMemoryEventStore


def _make_eff(**overrides: bool) -> EffectiveUniversalCritique:
    """Reused from fo90."""
    defaults: dict[str, bool] = {
        "impl_llm": False,
        "impl_stub": False,
        "impl_stage_failed_on_gate_fail": False,
        "impl_emit_finding_on_gate_fail": False,
        "impl_hard_block_on_gate_fail": False,
        "tw_enabled": False,
        "tw_llm": False,
        "tw_stub": False,
        "tw_stage_failed_on_gate_fail": False,
        "tw_emit_finding_on_gate_fail": False,
        "tw_hard_block_on_gate_fail": False,
        "pll_enabled": False,
        "pll_llm": False,
        "pll_stub": False,
        "pll_stage_failed_on_gate_fail": False,
        "pll_emit_finding_on_gate_fail": False,
        "pll_hard_block_on_gate_fail": False,
        "fw_enabled": False,
        "fw_llm": False,
        "fw_stub": False,
        "fw_stage_failed_on_gate_fail": False,
        "fw_emit_finding_on_gate_fail": False,
        "fw_hard_block_on_gate_fail": False,
        "mi_enabled": False,
        "mi_llm": False,
        "mi_stub": False,
        "mi_stage_failed_on_gate_fail": False,
        "mi_emit_finding_on_gate_fail": False,
        "mi_hard_block_on_gate_fail": False,
    }
    defaults.update(overrides)
    return EffectiveUniversalCritique(**defaults)


def _append_gate(
    mem: InMemoryEventStore,
    rid: UUID,
    stage_name: str,
    verdict: Verdict,
) -> None:
    """Append a synthesized ``gate.decision.emitted`` row.

    GateDecisionEmittedPayload requires FAIL verdicts to carry at least one
    of failing_critics / failing_finding_ids / non-empty failure_reason_code;
    we default to a synthetic reason code for FAIL so call-sites stay compact
    (mirrors fo89's helper).
    """
    code = "llm_gate_fail" if verdict == Verdict.FAIL else None
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
            ),
        ),
    )


def _append_prior_stage_failed(
    mem: InMemoryEventStore,
    rid: UUID,
    stage_name: str,
    reason_code: str,
) -> None:
    """Synthesize a prior ``stage.failed`` row for already-emitted dedup tests."""
    mem.append(
        StageFailedEvent(
            event_type=EventType.STAGE_FAILED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=StageFailedPayload(
                stage_name=stage_name,
                reason_code=reason_code,
                message=f"{stage_name} pre-seeded",
            ),
        ),
    )


def _stage_failed_rows_for(
    mem: InMemoryEventStore,
    rid: UUID,
    reason_code: str,
) -> list[dict[str, Any]]:
    """Filter ``stage.failed`` rows in the store matching ``reason_code``."""
    return [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == EventType.STAGE_FAILED.value
        and (r.get("payload") or {}).get("reason_code") == reason_code
    ]


def test_stage_failed_for_critique_gate_fail_multi_stage_matrix_4_axis() -> None:
    """Pin multi-stage permutations across the trio.

    A1 -- all-3 stages FAIL + all-3 flags on -> 3 STAGE_FAILED rows
    (one per stage with correct reason_code).
    A2 -- mixed verdict (impl PASS, tw FAIL, pll FAIL) + all-3 flags on
    -> 2 STAGE_FAILED rows (no impl_critique_gate_fail).
    A3 -- stage-filter isolation: tw + pll FAIL gates present + impl flag
    enabled but no impl gate -> 0 emits (cross-stage gates do not match).
    A4 -- already-emitted isolation: pre-seeded impl STAGE_FAILED + fresh
    FAIL gate + impl flag on -> still 1 row (pre-seeded), no duplicate.
    """
    eff_all_on = _make_eff(
        impl_stage_failed_on_gate_fail=True,
        tw_stage_failed_on_gate_fail=True,
        pll_stage_failed_on_gate_fail=True,
    )

    orch_a1, mem_a1 = make_dev_orchestrator()
    rid_a1 = orch_a1.create_run("default")
    _append_gate(mem_a1, rid_a1, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
    _append_gate(mem_a1, rid_a1, TEST_WRITER_CRITIQUE_STAGE, Verdict.FAIL)
    _append_gate(mem_a1, rid_a1, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
    orch_a1._maybe_emit_stage_failed_for_implementation_critique_gate_fail(  # noqa: SLF001
        rid_a1,
        eff_all_on,
    )
    orch_a1._maybe_emit_stage_failed_for_test_writer_critique_gate_fail(  # noqa: SLF001
        rid_a1,
        eff_all_on,
    )
    orch_a1._maybe_emit_stage_failed_for_planner_critique_gate_fail(  # noqa: SLF001
        rid_a1,
        eff_all_on,
    )
    assert len(_stage_failed_rows_for(mem_a1, rid_a1, "implementation_critique_gate_fail")) == 1
    assert len(_stage_failed_rows_for(mem_a1, rid_a1, "test_writer_critique_gate_fail")) == 1
    assert len(_stage_failed_rows_for(mem_a1, rid_a1, "planner_critique_gate_fail")) == 1

    orch_a2, mem_a2 = make_dev_orchestrator()
    rid_a2 = orch_a2.create_run("default")
    _append_gate(mem_a2, rid_a2, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.PASS)
    _append_gate(mem_a2, rid_a2, TEST_WRITER_CRITIQUE_STAGE, Verdict.FAIL)
    _append_gate(mem_a2, rid_a2, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
    orch_a2._maybe_emit_stage_failed_for_implementation_critique_gate_fail(  # noqa: SLF001
        rid_a2,
        eff_all_on,
    )
    orch_a2._maybe_emit_stage_failed_for_test_writer_critique_gate_fail(  # noqa: SLF001
        rid_a2,
        eff_all_on,
    )
    orch_a2._maybe_emit_stage_failed_for_planner_critique_gate_fail(  # noqa: SLF001
        rid_a2,
        eff_all_on,
    )
    assert len(_stage_failed_rows_for(mem_a2, rid_a2, "implementation_critique_gate_fail")) == 0, (
        "A2: impl gate PASS must suppress impl stage.failed even with flag on"
    )
    assert len(_stage_failed_rows_for(mem_a2, rid_a2, "test_writer_critique_gate_fail")) == 1
    assert len(_stage_failed_rows_for(mem_a2, rid_a2, "planner_critique_gate_fail")) == 1

    orch_a3, mem_a3 = make_dev_orchestrator()
    rid_a3 = orch_a3.create_run("default")
    _append_gate(mem_a3, rid_a3, TEST_WRITER_CRITIQUE_STAGE, Verdict.FAIL)
    _append_gate(mem_a3, rid_a3, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
    orch_a3._maybe_emit_stage_failed_for_implementation_critique_gate_fail(  # noqa: SLF001
        rid_a3,
        _make_eff(impl_stage_failed_on_gate_fail=True),
    )
    assert len(_stage_failed_rows_for(mem_a3, rid_a3, "implementation_critique_gate_fail")) == 0, (
        "A3: tw + pll FAIL gates must not cross-pollinate the impl emitter (stage-name filter)"
    )

    orch_a4, mem_a4 = make_dev_orchestrator()
    rid_a4 = orch_a4.create_run("default")
    _append_prior_stage_failed(
        mem_a4,
        rid_a4,
        IMPLEMENTATION_CRITIQUE_STAGE,
        "implementation_critique_gate_fail",
    )
    _append_gate(mem_a4, rid_a4, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
    orch_a4._maybe_emit_stage_failed_for_implementation_critique_gate_fail(  # noqa: SLF001
        rid_a4,
        _make_eff(impl_stage_failed_on_gate_fail=True),
    )
    assert len(_stage_failed_rows_for(mem_a4, rid_a4, "implementation_critique_gate_fail")) == 1, (
        "A4: pre-seeded STAGE_FAILED must short-circuit (reason_code dedup)"
    )


def test_stage_failed_for_critique_gate_fail_skip_branches_per_variant_4_axis_x_3() -> None:
    """Pin each of the 4 ``return`` arms in isolation per variant.

    Three sub-blocks (impl / tw / pll); each iterates the same 4 skip axes:

    B1 -- flag-off (master switch ``_stage_failed_on_gate_fail=False``)
    B2 -- already-emitted (reason_code matches pre-seeded STAGE_FAILED)
    B3 -- no gate row for THIS stage (FAIL gates for OTHER stages present)
    B4 -- last gate PASS (verdict suppression)
    """
    variants: list[tuple[str, str, str, str],] = [
        (
            "impl",
            "impl_stage_failed_on_gate_fail",
            IMPLEMENTATION_CRITIQUE_STAGE,
            "implementation_critique_gate_fail",
        ),
        (
            "tw",
            "tw_stage_failed_on_gate_fail",
            TEST_WRITER_CRITIQUE_STAGE,
            "test_writer_critique_gate_fail",
        ),
        (
            "pll",
            "pll_stage_failed_on_gate_fail",
            PLANNER_CRITIQUE_STAGE,
            "planner_critique_gate_fail",
        ),
    ]

    method_for: dict[str, str] = {
        "impl": "_maybe_emit_stage_failed_for_implementation_critique_gate_fail",
        "tw": "_maybe_emit_stage_failed_for_test_writer_critique_gate_fail",
        "pll": "_maybe_emit_stage_failed_for_planner_critique_gate_fail",
    }

    other_stage_for: dict[str, str] = {
        "impl": TEST_WRITER_CRITIQUE_STAGE,
        "tw": PLANNER_CRITIQUE_STAGE,
        "pll": IMPLEMENTATION_CRITIQUE_STAGE,
    }

    for variant, flag_name, stage_name, reason_code in variants:
        eff_off = _make_eff()
        eff_on = _make_eff(**{flag_name: True})

        orch_b1, mem_b1 = make_dev_orchestrator()
        rid_b1 = orch_b1.create_run("default")
        _append_gate(mem_b1, rid_b1, stage_name, Verdict.FAIL)
        getattr(orch_b1, method_for[variant])(rid_b1, eff_off)
        assert len(_stage_failed_rows_for(mem_b1, rid_b1, reason_code)) == 0, (
            f"B1[{variant}]: flag off must short-circuit before any emit"
        )

        orch_b2, mem_b2 = make_dev_orchestrator()
        rid_b2 = orch_b2.create_run("default")
        _append_prior_stage_failed(mem_b2, rid_b2, stage_name, reason_code)
        _append_gate(mem_b2, rid_b2, stage_name, Verdict.FAIL)
        getattr(orch_b2, method_for[variant])(rid_b2, eff_on)
        assert len(_stage_failed_rows_for(mem_b2, rid_b2, reason_code)) == 1, (
            f"B2[{variant}]: matching pre-seeded reason_code must dedup"
        )

        orch_b3, mem_b3 = make_dev_orchestrator()
        rid_b3 = orch_b3.create_run("default")
        _append_gate(mem_b3, rid_b3, other_stage_for[variant], Verdict.FAIL)
        getattr(orch_b3, method_for[variant])(rid_b3, eff_on)
        assert len(_stage_failed_rows_for(mem_b3, rid_b3, reason_code)) == 0, (
            f"B3[{variant}]: FAIL gate for OTHER stage must not match (stage-name filter)"
        )

        orch_b4, mem_b4 = make_dev_orchestrator()
        rid_b4 = orch_b4.create_run("default")
        _append_gate(mem_b4, rid_b4, stage_name, Verdict.PASS)
        getattr(orch_b4, method_for[variant])(rid_b4, eff_on)
        assert len(_stage_failed_rows_for(mem_b4, rid_b4, reason_code)) == 0, (
            f"B4[{variant}]: last gate PASS must suppress emit"
        )


def test_stage_failed_for_critique_gate_fail_payload_shape_per_variant_3_axis() -> None:
    """Pin per-variant emitted STAGE_FAILED payload triplet.

    Each variant runs the HAPPY path with the relevant flag on and a FAIL
    gate, then inspects the single emitted row's ``stage_name`` +
    ``reason_code`` + ``message`` (3 fields x 3 variants = 9 assertions).
    """
    cases: list[tuple[str, str, str, str, str]] = [
        (
            "_maybe_emit_stage_failed_for_implementation_critique_gate_fail",
            "impl_stage_failed_on_gate_fail",
            IMPLEMENTATION_CRITIQUE_STAGE,
            "implementation_critique_gate_fail",
            "implementation.critique gate verdict was FAIL",
        ),
        (
            "_maybe_emit_stage_failed_for_test_writer_critique_gate_fail",
            "tw_stage_failed_on_gate_fail",
            TEST_WRITER_CRITIQUE_STAGE,
            "test_writer_critique_gate_fail",
            "test_writer.critique gate verdict was FAIL",
        ),
        (
            "_maybe_emit_stage_failed_for_planner_critique_gate_fail",
            "pll_stage_failed_on_gate_fail",
            PLANNER_CRITIQUE_STAGE,
            "planner_critique_gate_fail",
            "planner.critique gate verdict was FAIL",
        ),
    ]
    for method_name, flag_name, stage_name, reason_code, expected_message in cases:
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("default")
        _append_gate(mem, rid, stage_name, Verdict.FAIL)
        getattr(orch, method_name)(rid, _make_eff(**{flag_name: True}))
        rows = _stage_failed_rows_for(mem, rid, reason_code)
        assert len(rows) == 1, f"{method_name}: HAPPY must emit exactly one row"
        pl = rows[0].get("payload") or {}
        assert pl.get("stage_name") == stage_name, (
            f"{method_name}: payload.stage_name must be {stage_name!r}"
        )
        assert pl.get("reason_code") == reason_code, (
            f"{method_name}: payload.reason_code must be {reason_code!r}"
        )
        assert pl.get("message") == expected_message, (
            f"{method_name}: payload.message must be {expected_message!r}"
        )


def test_stage_failed_for_critique_gate_fail_helper_contracts_5_axis() -> None:
    """Pin cross-cutting helper contracts using impl as the symmetric proxy.

    D1 -- ``eff=None`` lazy: ``_effective_universal_critique_for_run`` invoked
    once + emit happens (uses the mocked eff with impl flag on).
    D2 -- ``eff=<explicit>`` eager: ``_effective_universal_critique_for_run``
    NOT invoked (call_count == 0) + emit still happens.
    D3 -- LAST-wins (PASS -> FAIL): two gates for impl, last is FAIL -> emit.
    D4 -- LAST-wins (FAIL -> PASS): two gates for impl, last is PASS -> suppress.
    D5 -- verdict-string coercion (4 sub-axes): Verdict.FAIL enum / ``"FAIL"`` /
    ``"fail"`` lowercase / ``"Fail"`` mixed-case / ``" FAIL "`` whitespace
    each emits (pins ``str(verdict_raw).strip().upper() == "FAIL"``).
    """
    impl_method = "_maybe_emit_stage_failed_for_implementation_critique_gate_fail"

    orch_d1, mem_d1 = make_dev_orchestrator()
    rid_d1 = orch_d1.create_run("default")
    _append_gate(mem_d1, rid_d1, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
    eff_d1_on = _make_eff(impl_stage_failed_on_gate_fail=True)
    with patch.object(
        orch_d1,
        "_effective_universal_critique_for_run",
        return_value=eff_d1_on,
    ) as m_resolve:
        getattr(orch_d1, impl_method)(rid_d1)
    assert m_resolve.call_count == 1, (
        "D1: eff=None must lazily resolve via _effective_universal_critique_for_run"
    )
    assert len(_stage_failed_rows_for(mem_d1, rid_d1, "implementation_critique_gate_fail")) == 1, (
        "D1: lazy-resolved eff with flag on must still emit"
    )

    orch_d2, mem_d2 = make_dev_orchestrator()
    rid_d2 = orch_d2.create_run("default")
    _append_gate(mem_d2, rid_d2, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
    eff_d2_on = _make_eff(impl_stage_failed_on_gate_fail=True)
    with patch.object(
        orch_d2,
        "_effective_universal_critique_for_run",
    ) as m_resolve2:
        getattr(orch_d2, impl_method)(rid_d2, eff_d2_on)
    assert m_resolve2.call_count == 0, (
        "D2: explicit eff must bypass _effective_universal_critique_for_run "
        "(short-circuit on `if eff is not None`)"
    )
    assert len(_stage_failed_rows_for(mem_d2, rid_d2, "implementation_critique_gate_fail")) == 1, (
        "D2: explicit eff with flag on must still emit"
    )

    orch_d3, mem_d3 = make_dev_orchestrator()
    rid_d3 = orch_d3.create_run("default")
    _append_gate(mem_d3, rid_d3, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.PASS)
    _append_gate(mem_d3, rid_d3, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
    getattr(orch_d3, impl_method)(rid_d3, _make_eff(impl_stage_failed_on_gate_fail=True))
    assert len(_stage_failed_rows_for(mem_d3, rid_d3, "implementation_critique_gate_fail")) == 1, (
        "D3: LAST-wins -- PASS then FAIL means last verdict is FAIL -> emit"
    )

    orch_d4, mem_d4 = make_dev_orchestrator()
    rid_d4 = orch_d4.create_run("default")
    _append_gate(mem_d4, rid_d4, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
    _append_gate(mem_d4, rid_d4, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.PASS)
    getattr(orch_d4, impl_method)(rid_d4, _make_eff(impl_stage_failed_on_gate_fail=True))
    assert len(_stage_failed_rows_for(mem_d4, rid_d4, "implementation_critique_gate_fail")) == 0, (
        "D4: LAST-wins -- FAIL then PASS means last verdict is PASS -> suppress"
    )

    coercion_variants: list[str] = ["FAIL", "fail", "Fail", " FAIL "]
    for coerce_value in coercion_variants:
        orch_d5, mem_d5 = make_dev_orchestrator()
        rid_d5 = orch_d5.create_run("default")
        _append_gate(mem_d5, rid_d5, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
        mem_d5._rows[-1]["payload"]["verdict"] = coerce_value  # noqa: SLF001
        getattr(orch_d5, impl_method)(rid_d5, _make_eff(impl_stage_failed_on_gate_fail=True))
        assert (
            len(_stage_failed_rows_for(mem_d5, rid_d5, "implementation_critique_gate_fail")) == 1
        ), (
            f"D5: verdict-string coercion must accept {coerce_value!r} via "
            "str(verdict_raw).strip().upper() == 'FAIL' fallback"
        )
