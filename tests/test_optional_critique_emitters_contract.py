"""_emit_test_writer_critique_optional`` + ``_emit_planner_critique_optional``."""


from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import patch
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    ModelSelectedPrimaryEvent,
    ModelSelectedPrimaryPayload,
)
from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.workflow_universal_critique import EffectiveUniversalCritique

if TYPE_CHECKING:
    from hermes_store.memory import InMemoryEventStore


def _make_eff(**overrides: bool) -> EffectiveUniversalCritique:
    """Reused from fo90: all 17 flags default False, overrides flip selectively."""
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


def _append_model_selected_primary(
    mem: InMemoryEventStore,
    rid: UUID,
    model_id: str = "llama3.1:8b",
) -> None:
    """Append a synthetic MODEL_SELECTED_PRIMARY row so _selected_model_for_run hits."""
    mem.append(
        ModelSelectedPrimaryEvent(
            event_type=EventType.MODEL_SELECTED_PRIMARY,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=ModelSelectedPrimaryPayload(
                provider="ollama",
                model_id=model_id,
            ),
        ),
    )


def test_emit_test_writer_critique_optional_path_matrix_6_axis() -> None:
    """Pin the 6-path control flow at pipeline.py:1018-1060 for tw.

    A1 -- master tw_enabled=False -> no LLM, no stub.
    A2 -- enabled + llm=False + stub=False -> no LLM, no stub.
    A3 -- enabled + llm=False + stub=True -> stub-only.
    A4 -- enabled + llm=True + no model selected + stub=True ->
    LLM NOT invoked (model is None); stub fallback runs.
    A5 -- enabled + llm=True + model + LLM returns True + stub=True
    -> LLM only (stub NOT called per ``if not emitted_tw_llm``).
    A6 -- enabled + llm=True + model + LLM returns False + stub=True
    -> LLM + stub fallback (AND-gated fallback).
    """
    with (
        patch("hermes_orchestrator.pipeline.execute_test_writer_critique_llm") as m_llm,
        patch(
            "hermes_orchestrator.pipeline.emit_stub_test_writer_critique_panel",
        ) as m_stub,
    ):
        m_llm.return_value = True

        orch_a1, mem_a1 = make_dev_orchestrator()
        rid_a1 = orch_a1.create_run("default")
        _append_model_selected_primary(mem_a1, rid_a1)
        eff_a1 = _make_eff(
            tw_enabled=False,
            tw_llm=True,
            tw_stub=True,
        )
        orch_a1._emit_test_writer_critique_optional(  # noqa: SLF001
            rid_a1,
            verifier_exit_code=0,
            log_snippet="ok",
            eff=eff_a1,
        )
        assert m_llm.call_count == 0 and m_stub.call_count == 0, (
            "A1: master tw_enabled=False must short-circuit before any work"
        )

        m_llm.reset_mock()
        m_stub.reset_mock()
        orch_a2, _ = make_dev_orchestrator()
        rid_a2 = orch_a2.create_run("default")
        eff_a2 = _make_eff(tw_enabled=True, tw_llm=False, tw_stub=False)
        orch_a2._emit_test_writer_critique_optional(  # noqa: SLF001
            rid_a2,
            verifier_exit_code=0,
            log_snippet="ok",
            eff=eff_a2,
        )
        assert m_llm.call_count == 0 and m_stub.call_count == 0, (
            "A2: enabled + llm=False + stub=False -> no work"
        )

        m_llm.reset_mock()
        m_stub.reset_mock()
        orch_a3, _ = make_dev_orchestrator()
        rid_a3 = orch_a3.create_run("default")
        eff_a3 = _make_eff(tw_enabled=True, tw_llm=False, tw_stub=True)
        orch_a3._emit_test_writer_critique_optional(  # noqa: SLF001
            rid_a3,
            verifier_exit_code=0,
            log_snippet="ok",
            eff=eff_a3,
        )
        assert m_llm.call_count == 0 and m_stub.call_count == 1, (
            "A3: enabled + llm=False + stub=True -> stub-only path (no LLM attempted)"
        )

        m_llm.reset_mock()
        m_stub.reset_mock()
        orch_a4, _ = make_dev_orchestrator()
        rid_a4 = orch_a4.create_run("default")
        eff_a4 = _make_eff(tw_enabled=True, tw_llm=True, tw_stub=True)
        orch_a4._emit_test_writer_critique_optional(  # noqa: SLF001
            rid_a4,
            verifier_exit_code=0,
            log_snippet="ok",
            eff=eff_a4,
        )
        assert m_llm.call_count == 0 and m_stub.call_count == 1, (
            "A4: enabled + llm=True + no model selected -> LLM NOT invoked; "
            "stub fallback runs because emitted_tw_llm stayed False"
        )

        m_llm.reset_mock()
        m_stub.reset_mock()
        m_llm.return_value = True
        orch_a5, mem_a5 = make_dev_orchestrator()
        rid_a5 = orch_a5.create_run("default")
        _append_model_selected_primary(mem_a5, rid_a5)
        eff_a5 = _make_eff(tw_enabled=True, tw_llm=True, tw_stub=True)
        orch_a5._emit_test_writer_critique_optional(  # noqa: SLF001
            rid_a5,
            verifier_exit_code=0,
            log_snippet="ok",
            eff=eff_a5,
        )
        assert m_llm.call_count == 1 and m_stub.call_count == 0, (
            "A5: LLM returns True -> stub NOT invoked even with stub=True"
        )

        m_llm.reset_mock()
        m_stub.reset_mock()
        m_llm.return_value = False
        orch_a6, mem_a6 = make_dev_orchestrator()
        rid_a6 = orch_a6.create_run("default")
        _append_model_selected_primary(mem_a6, rid_a6)
        eff_a6 = _make_eff(tw_enabled=True, tw_llm=True, tw_stub=True)
        orch_a6._emit_test_writer_critique_optional(  # noqa: SLF001
            rid_a6,
            verifier_exit_code=0,
            log_snippet="ok",
            eff=eff_a6,
        )
        assert m_llm.call_count == 1 and m_stub.call_count == 1, (
            "A6: LLM returns False + stub=True -> LLM + stub fallback "
            "(AND-gated fallback)"
        )


def test_emit_planner_critique_optional_path_matrix_6_axis() -> None:
    """Pin the 6-path control flow at pipeline.py:1062-1103 for planner.

    Mirrors Part A with ``pll_*`` flags + ``execute_planner_critique_llm`` +
    ``emit_stub_planner_critique_panel`` patches. Six axes (B1-B6) parallel
    to A1-A6 prove symmetric implementation across the two methods.
    """
    with (
        patch("hermes_orchestrator.pipeline.execute_planner_critique_llm") as m_llm,
        patch(
            "hermes_orchestrator.pipeline.emit_stub_planner_critique_panel",
        ) as m_stub,
    ):
        m_llm.return_value = True

        orch_b1, mem_b1 = make_dev_orchestrator()
        rid_b1 = orch_b1.create_run("default")
        _append_model_selected_primary(mem_b1, rid_b1)
        eff_b1 = _make_eff(
            pll_enabled=False,
            pll_llm=True,
            pll_stub=True,
        )
        orch_b1._emit_planner_critique_optional(  # noqa: SLF001
            rid_b1,
            verifier_exit_code=0,
            log_snippet="ok",
            eff=eff_b1,
        )
        assert m_llm.call_count == 0 and m_stub.call_count == 0, (
            "B1: master pll_enabled=False must short-circuit"
        )

        m_llm.reset_mock()
        m_stub.reset_mock()
        orch_b2, _ = make_dev_orchestrator()
        rid_b2 = orch_b2.create_run("default")
        eff_b2 = _make_eff(pll_enabled=True, pll_llm=False, pll_stub=False)
        orch_b2._emit_planner_critique_optional(  # noqa: SLF001
            rid_b2,
            verifier_exit_code=0,
            log_snippet="ok",
            eff=eff_b2,
        )
        assert m_llm.call_count == 0 and m_stub.call_count == 0, (
            "B2: enabled + llm=False + stub=False -> no work"
        )

        m_llm.reset_mock()
        m_stub.reset_mock()
        orch_b3, _ = make_dev_orchestrator()
        rid_b3 = orch_b3.create_run("default")
        eff_b3 = _make_eff(pll_enabled=True, pll_llm=False, pll_stub=True)
        orch_b3._emit_planner_critique_optional(  # noqa: SLF001
            rid_b3,
            verifier_exit_code=0,
            log_snippet="ok",
            eff=eff_b3,
        )
        assert m_llm.call_count == 0 and m_stub.call_count == 1, (
            "B3: enabled + llm=False + stub=True -> stub-only path"
        )

        m_llm.reset_mock()
        m_stub.reset_mock()
        orch_b4, _ = make_dev_orchestrator()
        rid_b4 = orch_b4.create_run("default")
        eff_b4 = _make_eff(pll_enabled=True, pll_llm=True, pll_stub=True)
        orch_b4._emit_planner_critique_optional(  # noqa: SLF001
            rid_b4,
            verifier_exit_code=0,
            log_snippet="ok",
            eff=eff_b4,
        )
        assert m_llm.call_count == 0 and m_stub.call_count == 1, (
            "B4: enabled + llm=True + no model -> LLM NOT invoked; stub fallback runs"
        )

        m_llm.reset_mock()
        m_stub.reset_mock()
        m_llm.return_value = True
        orch_b5, mem_b5 = make_dev_orchestrator()
        rid_b5 = orch_b5.create_run("default")
        _append_model_selected_primary(mem_b5, rid_b5)
        eff_b5 = _make_eff(pll_enabled=True, pll_llm=True, pll_stub=True)
        orch_b5._emit_planner_critique_optional(  # noqa: SLF001
            rid_b5,
            verifier_exit_code=0,
            log_snippet="ok",
            eff=eff_b5,
        )
        assert m_llm.call_count == 1 and m_stub.call_count == 0, (
            "B5: LLM returns True -> stub NOT invoked"
        )

        m_llm.reset_mock()
        m_stub.reset_mock()
        m_llm.return_value = False
        orch_b6, mem_b6 = make_dev_orchestrator()
        rid_b6 = orch_b6.create_run("default")
        _append_model_selected_primary(mem_b6, rid_b6)
        eff_b6 = _make_eff(pll_enabled=True, pll_llm=True, pll_stub=True)
        orch_b6._emit_planner_critique_optional(  # noqa: SLF001
            rid_b6,
            verifier_exit_code=0,
            log_snippet="ok",
            eff=eff_b6,
        )
        assert m_llm.call_count == 1 and m_stub.call_count == 1, (
            "B6: LLM returns False + stub=True -> LLM + stub fallback"
        )


def test_emit_test_writer_critique_optional_argument_propagation_5_axis() -> None:
    """Pin the LLM call's kwargs contract at pipeline.py:1043-1053 for tw.

    All axes use the happy path (enabled + llm + model + stub=False).
    Each axis inspects ``m_llm.call_args.kwargs``.

    C1 -- base_url default ``"http://localhost:11434"`` when _base_cfg = {}.
    C2 -- base_url override from _base_cfg runtime.base_url.
    C3 -- timeout_seconds default 120.0 + float type when _base_cfg = {}.
    C4 -- timeout_seconds int->float cast when _base_cfg has int value.
    C5 -- run_id + model_id + verifier_exit_code + log_snippet
    verbatim 4-kwarg pass-through.
    """
    eff = _make_eff(tw_enabled=True, tw_llm=True, tw_stub=False)

    with (
        patch("hermes_orchestrator.pipeline.execute_test_writer_critique_llm") as m_llm,
        patch("hermes_orchestrator.pipeline.emit_stub_test_writer_critique_panel"),
    ):
        m_llm.return_value = True

        orch_c1, mem_c1 = make_dev_orchestrator()
        rid_c1 = orch_c1.create_run("default")
        _append_model_selected_primary(mem_c1, rid_c1)
        with patch.object(orch_c1, "_base_cfg", return_value={}):
            orch_c1._emit_test_writer_critique_optional(  # noqa: SLF001
                rid_c1,
                verifier_exit_code=0,
                log_snippet="ok",
                eff=eff,
            )
        assert m_llm.call_args.kwargs["base_url"] == "http://localhost:11434", (
            "C1: base_url must default to localhost:11434 when runtime config missing"
        )

        m_llm.reset_mock()
        m_llm.return_value = True
        orch_c2, mem_c2 = make_dev_orchestrator()
        rid_c2 = orch_c2.create_run("default")
        _append_model_selected_primary(mem_c2, rid_c2)
        with patch.object(
            orch_c2,
            "_base_cfg",
            return_value={"runtime": {"base_url": "http://example:9000"}},
        ):
            orch_c2._emit_test_writer_critique_optional(  # noqa: SLF001
                rid_c2,
                verifier_exit_code=0,
                log_snippet="ok",
                eff=eff,
            )
        assert m_llm.call_args.kwargs["base_url"] == "http://example:9000", (
            "C2: base_url must be read from _base_cfg runtime.base_url"
        )

        m_llm.reset_mock()
        m_llm.return_value = True
        orch_c3, mem_c3 = make_dev_orchestrator()
        rid_c3 = orch_c3.create_run("default")
        _append_model_selected_primary(mem_c3, rid_c3)
        with patch.object(orch_c3, "_base_cfg", return_value={}):
            orch_c3._emit_test_writer_critique_optional(  # noqa: SLF001
                rid_c3,
                verifier_exit_code=0,
                log_snippet="ok",
                eff=eff,
            )
        timeout_c3 = m_llm.call_args.kwargs["timeout_seconds"]
        assert timeout_c3 == 120.0, "C3: timeout_seconds must default to 120.0"
        assert isinstance(timeout_c3, float), (
            "C3: timeout_seconds must be float-typed even on default"
        )

        m_llm.reset_mock()
        m_llm.return_value = True
        orch_c4, mem_c4 = make_dev_orchestrator()
        rid_c4 = orch_c4.create_run("default")
        _append_model_selected_primary(mem_c4, rid_c4)
        with patch.object(
            orch_c4,
            "_base_cfg",
            return_value={"runtime": {"request_timeout_seconds": 30}},
        ):
            orch_c4._emit_test_writer_critique_optional(  # noqa: SLF001
                rid_c4,
                verifier_exit_code=0,
                log_snippet="ok",
                eff=eff,
            )
        timeout_c4 = m_llm.call_args.kwargs["timeout_seconds"]
        assert timeout_c4 == 30.0, "C4: timeout_seconds must propagate runtime override"
        assert isinstance(timeout_c4, float), (
            "C4: int request_timeout_seconds must be cast to float via float()"
        )

        m_llm.reset_mock()
        m_llm.return_value = True
        orch_c5, mem_c5 = make_dev_orchestrator()
        rid_c5 = orch_c5.create_run("default")
        _append_model_selected_primary(mem_c5, rid_c5, model_id="custom-model:13b")
        orch_c5._emit_test_writer_critique_optional(  # noqa: SLF001
            rid_c5,
            verifier_exit_code=42,
            log_snippet="LOG_X",
            eff=eff,
        )
        kw_c5 = m_llm.call_args.kwargs
        assert kw_c5["run_id"] == rid_c5, "C5: run_id must propagate verbatim"
        assert kw_c5["model_id"] == "custom-model:13b", (
            "C5: model_id must propagate from MODEL_SELECTED_PRIMARY payload"
        )
        assert kw_c5["verifier_exit_code"] == 42, (
            "C5: verifier_exit_code must propagate verbatim"
        )
        assert kw_c5["log_snippet"] == "LOG_X", (
            "C5: log_snippet must propagate verbatim"
        )


def test_emit_planner_critique_optional_argument_propagation_5_axis() -> None:
    """Pin the LLM call's kwargs contract at pipeline.py:1086-1096 for planner.

    Mirrors Part C for planner. Five axes (D1-D5) parallel to C1-C5 prove
    the call-argument contract is identical across both methods (both
    default base_url to ``"http://localhost:11434"``, both default
    timeout_seconds to ``120.0``, both cast via ``float()``, both pass
    model_id from the same ``_selected_model_for_run`` source).
    """
    eff = _make_eff(pll_enabled=True, pll_llm=True, pll_stub=False)

    with (
        patch("hermes_orchestrator.pipeline.execute_planner_critique_llm") as m_llm,
        patch("hermes_orchestrator.pipeline.emit_stub_planner_critique_panel"),
    ):
        m_llm.return_value = True

        orch_d1, mem_d1 = make_dev_orchestrator()
        rid_d1 = orch_d1.create_run("default")
        _append_model_selected_primary(mem_d1, rid_d1)
        with patch.object(orch_d1, "_base_cfg", return_value={}):
            orch_d1._emit_planner_critique_optional(  # noqa: SLF001
                rid_d1,
                verifier_exit_code=0,
                log_snippet="ok",
                eff=eff,
            )
        assert m_llm.call_args.kwargs["base_url"] == "http://localhost:11434", (
            "D1: base_url default must match tw's default (symmetric contract)"
        )

        m_llm.reset_mock()
        m_llm.return_value = True
        orch_d2, mem_d2 = make_dev_orchestrator()
        rid_d2 = orch_d2.create_run("default")
        _append_model_selected_primary(mem_d2, rid_d2)
        with patch.object(
            orch_d2,
            "_base_cfg",
            return_value={"runtime": {"base_url": "http://example:9000"}},
        ):
            orch_d2._emit_planner_critique_optional(  # noqa: SLF001
                rid_d2,
                verifier_exit_code=0,
                log_snippet="ok",
                eff=eff,
            )
        assert m_llm.call_args.kwargs["base_url"] == "http://example:9000", (
            "D2: base_url override path must work identically to tw"
        )

        m_llm.reset_mock()
        m_llm.return_value = True
        orch_d3, mem_d3 = make_dev_orchestrator()
        rid_d3 = orch_d3.create_run("default")
        _append_model_selected_primary(mem_d3, rid_d3)
        with patch.object(orch_d3, "_base_cfg", return_value={}):
            orch_d3._emit_planner_critique_optional(  # noqa: SLF001
                rid_d3,
                verifier_exit_code=0,
                log_snippet="ok",
                eff=eff,
            )
        timeout_d3 = m_llm.call_args.kwargs["timeout_seconds"]
        assert timeout_d3 == 120.0, "D3: timeout default must match tw"
        assert isinstance(timeout_d3, float), "D3: timeout must be float-typed on default"

        m_llm.reset_mock()
        m_llm.return_value = True
        orch_d4, mem_d4 = make_dev_orchestrator()
        rid_d4 = orch_d4.create_run("default")
        _append_model_selected_primary(mem_d4, rid_d4)
        with patch.object(
            orch_d4,
            "_base_cfg",
            return_value={"runtime": {"request_timeout_seconds": 30}},
        ):
            orch_d4._emit_planner_critique_optional(  # noqa: SLF001
                rid_d4,
                verifier_exit_code=0,
                log_snippet="ok",
                eff=eff,
            )
        timeout_d4 = m_llm.call_args.kwargs["timeout_seconds"]
        assert timeout_d4 == 30.0, "D4: timeout override must match tw"
        assert isinstance(timeout_d4, float), (
            "D4: int request_timeout_seconds must be cast to float (parallel to C4)"
        )

        m_llm.reset_mock()
        m_llm.return_value = True
        orch_d5, mem_d5 = make_dev_orchestrator()
        rid_d5 = orch_d5.create_run("default")
        _append_model_selected_primary(mem_d5, rid_d5, model_id="custom-model:13b")
        orch_d5._emit_planner_critique_optional(  # noqa: SLF001
            rid_d5,
            verifier_exit_code=42,
            log_snippet="LOG_X",
            eff=eff,
        )
        kw_d5 = m_llm.call_args.kwargs
        assert kw_d5["run_id"] == rid_d5, "D5: run_id must propagate verbatim"
        assert kw_d5["model_id"] == "custom-model:13b", (
            "D5: model_id must propagate from MODEL_SELECTED_PRIMARY (parallel to C5)"
        )
        assert kw_d5["verifier_exit_code"] == 42, (
            "D5: verifier_exit_code must propagate verbatim"
        )
        assert kw_d5["log_snippet"] == "LOG_X", (
            "D5: log_snippet must propagate verbatim"
        )
