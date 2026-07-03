from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import patch
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    Verdict,
)
from orchestrator.llm import (
    IMPLEMENTATION_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
)
from orchestrator.pipeline import make_dev_orchestrator
from orchestrator.workflow.universal_critique import EffectiveUniversalCritique

if TYPE_CHECKING:
    from store.memory import InMemoryEventStore


def _make_eff(**overrides: bool) -> EffectiveUniversalCritique:
    """Build an EffectiveUniversalCritique with ALL flags False; selectively override.

    Lets each axis flip only the flags it intends to test without restating
    the 17-field defaults inline.
    """
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


def _append_critique_gate(
    mem: InMemoryEventStore,
    rid: UUID,
    stage_name: str,
    verdict: Verdict,
) -> None:
    """Append one synthesized gate row; FAIL gets default failure_reason_code.

    GateDecisionEmittedPayload requires FAIL verdicts to carry at least one
    of failing_critics / failing_finding_ids / non-empty failure_reason_code;
    we default to a synthetic reason code here so call-sites stay compact.
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


def _rows_for(mem: InMemoryEventStore, rid: UUID) -> list[dict[str, Any]]:
    return mem.list_run_events(str(rid))


def test_critique_impl_hard_block_gate_fail_direct_contract_5_axis() -> None:
    orch_a1, mem_a1 = make_dev_orchestrator()
    rid_a1 = orch_a1.create_run("default")
    _append_critique_gate(mem_a1, rid_a1, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
    eff_a1 = _make_eff(
        impl_llm=True,
        impl_stub=True,
        impl_hard_block_on_gate_fail=False,
    )
    assert (
        orch_a1._critique_impl_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_a1, rid_a1),
            eff_a1,
        )
        is False
    ), "A1: hard_block off must short-circuit before the verdict read"

    orch_a2, mem_a2 = make_dev_orchestrator()
    rid_a2 = orch_a2.create_run("default")
    _append_critique_gate(mem_a2, rid_a2, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
    eff_a2 = _make_eff(impl_hard_block_on_gate_fail=True)
    assert (
        orch_a2._critique_impl_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_a2, rid_a2),
            eff_a2,
        )
        is False
    ), "A2: (llm OR stub) both False must short-circuit the second guard arm"

    orch_a3, mem_a3 = make_dev_orchestrator()
    rid_a3 = orch_a3.create_run("default")
    eff_a3 = _make_eff(impl_hard_block_on_gate_fail=True, impl_llm=True)
    assert (
        orch_a3._critique_impl_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_a3, rid_a3),
            eff_a3,
        )
        is False
    ), "A3 (empty rows): pl is None must short-circuit"

    _append_critique_gate(mem_a3, rid_a3, TEST_WRITER_CRITIQUE_STAGE, Verdict.FAIL)
    _append_critique_gate(mem_a3, rid_a3, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
    assert (
        orch_a3._critique_impl_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_a3, rid_a3),
            eff_a3,
        )
        is False
    ), (
        "A3 (stage filter): TW+planner FAIL gates present must NOT trip the "
        "impl helper -- _last_critique_gate_payload_for_stage returns None"
    )

    orch_a4, mem_a4 = make_dev_orchestrator()
    rid_a4 = orch_a4.create_run("default")
    _append_critique_gate(mem_a4, rid_a4, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.PASS)
    eff_a4 = _make_eff(impl_hard_block_on_gate_fail=True, impl_llm=True)
    assert (
        orch_a4._critique_impl_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_a4, rid_a4),
            eff_a4,
        )
        is False
    ), "A4: last impl gate PASS must not trip the helper"

    orch_a5, mem_a5 = make_dev_orchestrator()
    rid_a5 = orch_a5.create_run("default")
    _append_critique_gate(mem_a5, rid_a5, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
    eff_a5 = _make_eff(impl_hard_block_on_gate_fail=True, impl_llm=True)
    assert (
        orch_a5._critique_impl_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_a5, rid_a5),
            eff_a5,
        )
        is True
    ), "A5 HAPPY: guards pass + FAIL impl gate must return True"


def test_critique_tw_hard_block_gate_fail_direct_contract_6_axis() -> None:
    orch_b1, mem_b1 = make_dev_orchestrator()
    rid_b1 = orch_b1.create_run("default")
    _append_critique_gate(mem_b1, rid_b1, TEST_WRITER_CRITIQUE_STAGE, Verdict.FAIL)
    eff_b1 = _make_eff(
        tw_enabled=True,
        tw_llm=True,
        tw_stub=True,
        tw_hard_block_on_gate_fail=False,
    )
    assert (
        orch_b1._critique_tw_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_b1, rid_b1),
            eff_b1,
        )
        is False
    ), "B1: hard_block off must short-circuit"

    orch_b2, mem_b2 = make_dev_orchestrator()
    rid_b2 = orch_b2.create_run("default")
    _append_critique_gate(mem_b2, rid_b2, TEST_WRITER_CRITIQUE_STAGE, Verdict.FAIL)
    eff_b2 = _make_eff(
        tw_hard_block_on_gate_fail=True,
        tw_llm=True,
        tw_enabled=False,
    )
    assert (
        orch_b2._critique_tw_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_b2, rid_b2),
            eff_b2,
        )
        is False
    ), (
        "B2: tw_enabled=False must short-circuit -- this is the master "
        "switch arm absent in the impl helper"
    )

    orch_b3, mem_b3 = make_dev_orchestrator()
    rid_b3 = orch_b3.create_run("default")
    _append_critique_gate(mem_b3, rid_b3, TEST_WRITER_CRITIQUE_STAGE, Verdict.FAIL)
    eff_b3 = _make_eff(tw_hard_block_on_gate_fail=True, tw_enabled=True)
    assert (
        orch_b3._critique_tw_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_b3, rid_b3),
            eff_b3,
        )
        is False
    ), "B3: (llm OR stub) both False must short-circuit"

    orch_b4, mem_b4 = make_dev_orchestrator()
    rid_b4 = orch_b4.create_run("default")
    _append_critique_gate(mem_b4, rid_b4, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
    _append_critique_gate(mem_b4, rid_b4, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
    eff_b4 = _make_eff(
        tw_hard_block_on_gate_fail=True,
        tw_enabled=True,
        tw_llm=True,
    )
    assert (
        orch_b4._critique_tw_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_b4, rid_b4),
            eff_b4,
        )
        is False
    ), "B4: no TW gate row -- impl+planner FAIL gates must NOT trip tw helper"

    orch_b5, mem_b5 = make_dev_orchestrator()
    rid_b5 = orch_b5.create_run("default")
    _append_critique_gate(mem_b5, rid_b5, TEST_WRITER_CRITIQUE_STAGE, Verdict.PASS)
    eff_b5 = _make_eff(
        tw_hard_block_on_gate_fail=True,
        tw_enabled=True,
        tw_llm=True,
    )
    assert (
        orch_b5._critique_tw_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_b5, rid_b5),
            eff_b5,
        )
        is False
    ), "B5: last TW gate PASS must not trip the helper"

    orch_b6, mem_b6 = make_dev_orchestrator()
    rid_b6 = orch_b6.create_run("default")
    _append_critique_gate(mem_b6, rid_b6, TEST_WRITER_CRITIQUE_STAGE, Verdict.FAIL)
    eff_b6 = _make_eff(
        tw_hard_block_on_gate_fail=True,
        tw_enabled=True,
        tw_llm=True,
    )
    assert (
        orch_b6._critique_tw_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_b6, rid_b6),
            eff_b6,
        )
        is True
    ), "B6 HAPPY: guards pass + FAIL TW gate must return True"


def test_critique_pll_hard_block_gate_fail_direct_contract_6_axis() -> None:
    orch_c1, mem_c1 = make_dev_orchestrator()
    rid_c1 = orch_c1.create_run("default")
    _append_critique_gate(mem_c1, rid_c1, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
    eff_c1 = _make_eff(
        pll_enabled=True,
        pll_llm=True,
        pll_stub=True,
        pll_hard_block_on_gate_fail=False,
    )
    assert (
        orch_c1._critique_pll_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_c1, rid_c1),
            eff_c1,
        )
        is False
    ), "C1: hard_block off must short-circuit"

    orch_c2, mem_c2 = make_dev_orchestrator()
    rid_c2 = orch_c2.create_run("default")
    _append_critique_gate(mem_c2, rid_c2, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
    eff_c2 = _make_eff(
        pll_hard_block_on_gate_fail=True,
        pll_llm=True,
        pll_enabled=False,
    )
    assert (
        orch_c2._critique_pll_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_c2, rid_c2),
            eff_c2,
        )
        is False
    ), (
        "C2: pll_enabled=False master switch must short-circuit (parallel to "
        "B2 for tw; this asymmetric guard does not exist in impl)"
    )

    orch_c3, mem_c3 = make_dev_orchestrator()
    rid_c3 = orch_c3.create_run("default")
    _append_critique_gate(mem_c3, rid_c3, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
    eff_c3 = _make_eff(pll_hard_block_on_gate_fail=True, pll_enabled=True)
    assert (
        orch_c3._critique_pll_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_c3, rid_c3),
            eff_c3,
        )
        is False
    ), "C3: (llm OR stub) both False must short-circuit"

    orch_c4, mem_c4 = make_dev_orchestrator()
    rid_c4 = orch_c4.create_run("default")
    _append_critique_gate(mem_c4, rid_c4, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
    _append_critique_gate(mem_c4, rid_c4, TEST_WRITER_CRITIQUE_STAGE, Verdict.FAIL)
    eff_c4 = _make_eff(
        pll_hard_block_on_gate_fail=True,
        pll_enabled=True,
        pll_llm=True,
    )
    assert (
        orch_c4._critique_pll_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_c4, rid_c4),
            eff_c4,
        )
        is False
    ), (
        "C4: no planner gate row -- impl+TW FAIL gates must NOT trip pll helper "
        "(stage-name filter symmetry with B4)"
    )

    orch_c5, mem_c5 = make_dev_orchestrator()
    rid_c5 = orch_c5.create_run("default")
    _append_critique_gate(mem_c5, rid_c5, PLANNER_CRITIQUE_STAGE, Verdict.PASS)
    eff_c5 = _make_eff(
        pll_hard_block_on_gate_fail=True,
        pll_enabled=True,
        pll_llm=True,
    )
    assert (
        orch_c5._critique_pll_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_c5, rid_c5),
            eff_c5,
        )
        is False
    ), "C5: last planner gate PASS must not trip the helper"

    orch_c6, mem_c6 = make_dev_orchestrator()
    rid_c6 = orch_c6.create_run("default")
    _append_critique_gate(mem_c6, rid_c6, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
    eff_c6 = _make_eff(
        pll_hard_block_on_gate_fail=True,
        pll_enabled=True,
        pll_llm=True,
    )
    assert (
        orch_c6._critique_pll_hard_block_gate_fail(  # noqa: SLF001
            _rows_for(mem_c6, rid_c6),
            eff_c6,
        )
        is True
    ), "C6 HAPPY: guards pass + FAIL planner gate must return True"


def test_should_skip_critique_downstream_tail_aggregator_5_axis() -> None:
    orch_d1, _mem_d1 = make_dev_orchestrator()
    rid_d1 = orch_d1.create_run("default")
    eff_d1 = _make_eff()
    assert orch_d1._should_skip_critique_downstream_tail(rid_d1, eff_d1) is False, (  # noqa: SLF001
        "D1: all-off baseline -- none of the trio's first-guard arms pass"
    )

    orch_d2, mem_d2 = make_dev_orchestrator()
    rid_d2 = orch_d2.create_run("default")
    _append_critique_gate(mem_d2, rid_d2, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.FAIL)
    eff_d2 = _make_eff(impl_hard_block_on_gate_fail=True, impl_llm=True)
    assert orch_d2._should_skip_critique_downstream_tail(rid_d2, eff_d2) is True, (  # noqa: SLF001
        "D2: only impl helper returns True; aggregator returns True via first arm"
    )

    orch_d3, mem_d3 = make_dev_orchestrator()
    rid_d3 = orch_d3.create_run("default")
    _append_critique_gate(mem_d3, rid_d3, TEST_WRITER_CRITIQUE_STAGE, Verdict.FAIL)
    eff_d3 = _make_eff(
        tw_hard_block_on_gate_fail=True,
        tw_enabled=True,
        tw_llm=True,
    )
    assert orch_d3._should_skip_critique_downstream_tail(rid_d3, eff_d3) is True, (  # noqa: SLF001
        "D3: only tw helper returns True; aggregator returns True via second arm"
    )

    orch_d4, mem_d4 = make_dev_orchestrator()
    rid_d4 = orch_d4.create_run("default")
    _append_critique_gate(mem_d4, rid_d4, PLANNER_CRITIQUE_STAGE, Verdict.FAIL)
    eff_d4 = _make_eff(
        pll_hard_block_on_gate_fail=True,
        pll_enabled=True,
        pll_llm=True,
    )
    assert orch_d4._should_skip_critique_downstream_tail(rid_d4, eff_d4) is True, (  # noqa: SLF001
        "D4: only pll helper returns True; aggregator returns True via third arm"
    )

    orch_d5, _mem_d5 = make_dev_orchestrator()
    rid_d5 = orch_d5.create_run("default")
    eff_d5 = _make_eff()
    with (
        patch.object(
            orch_d5,
            "_critique_impl_hard_block_gate_fail",
            return_value=True,
        ) as m_impl,
        patch.object(
            orch_d5,
            "_critique_tw_hard_block_gate_fail",
            return_value=False,
        ) as m_tw,
        patch.object(
            orch_d5,
            "_critique_pll_hard_block_gate_fail",
            return_value=False,
        ) as m_pll,
    ):
        result = orch_d5._should_skip_critique_downstream_tail(rid_d5, eff_d5)  # noqa: SLF001
    assert result is True
    assert m_impl.call_count == 1, "D5: impl helper must be evaluated first"
    assert m_tw.call_count == 0, (
        "D5: tw helper must NOT be invoked when impl returns True (or short-circuit)"
    )
    assert m_pll.call_count == 0, (
        "D5: pll helper must NOT be invoked when impl returns True (or short-circuit)"
    )
