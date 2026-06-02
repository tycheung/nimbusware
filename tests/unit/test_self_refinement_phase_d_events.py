from __future__ import annotations

import os
from unittest.mock import patch

from hermes_orchestrator.pipeline import make_dev_orchestrator


def test_self_refinement_marker_emits_phase_d_loop_signal() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run(
        "self_refinement_on",
        business_area_persona_id="commerce",
        development_role_persona_id="backend_engineer",
    )
    with patch.dict(os.environ, {"HERMES_SELF_REFINEMENT_STAGE_MARKER": "1"}, clear=False):
        orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    rows = mem.list_run_events(str(rid))
    phase_d = [r for r in rows if r.get("event_type") == "self_refinement.loop.signalled"]
    assert len(phase_d) == 1
    payload = phase_d[0].get("payload") or {}
    assert payload.get("phase") == "D"
    assert payload.get("signal") == "phase_d_kickoff"
    assert payload.get("attempt") == 1
    assert payload.get("stage_name") == "self_refinement:policy"
    assert payload.get("gate_decision") in {"proceed", "hold"}
    assert payload.get("evaluation_status") in {"ok", "invalid", "gap"}
    assert payload.get("loops_remaining") == 2
    assert payload.get("orchestration_branch") == "rules"
    assert payload.get("llm_critique_enabled") is True


def test_self_refinement_marker_llm_critique_branch_when_hold() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run(
        "self_refinement_on",
        business_area_persona_id="commerce",
        development_role_persona_id="backend_engineer",
    )
    env = {
        "HERMES_SELF_REFINEMENT_STAGE_MARKER": "1",
        "HERMES_USE_LLM": "1",
    }
    with patch.dict(os.environ, env, clear=False):
        with patch.object(orch, "_selected_model_for_run", return_value="m"):
            with patch(
                "hermes_orchestrator.pipeline.execute_self_refinement_critique_llm",
                return_value={
                    "verdict": "PASS",
                    "gate_decision": "proceed",
                    "summary": "minor gaps only",
                },
            ):
                orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    rows = mem.list_run_events(str(rid))
    phase_d = [r for r in rows if r.get("event_type") == "self_refinement.loop.signalled"]
    assert len(phase_d) == 1
    payload = phase_d[0].get("payload") or {}
    if payload.get("gate_decision") == "hold":
        assert payload.get("orchestration_branch") == "rules_with_llm_critique"
        assert payload.get("llm_critique_attempted") is True
        assert payload.get("llm_critique_verdict") == "PASS"
        assert payload.get("llm_gate_decision") == "proceed"


def test_self_refinement_stub_critique_panel_when_llm_misses() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run(
        "self_refinement_on",
        business_area_persona_id="commerce",
        development_role_persona_id="backend_engineer",
    )
    env = {
        "HERMES_SELF_REFINEMENT_STAGE_MARKER": "1",
        "HERMES_USE_LLM": "1",
        "HERMES_SELF_REFINEMENT_CRITIQUE_STUB": "1",
    }
    with patch.dict(os.environ, env, clear=False):
        with patch.object(orch, "_selected_model_for_run", return_value="m"):
            with patch(
                "hermes_orchestrator.pipeline.execute_self_refinement_critique_llm",
                return_value=None,
            ):
                orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    rows = mem.list_run_events(str(rid))
    gates = [
        r
        for r in rows
        if r.get("event_type") == "gate.decision.emitted"
        and (r.get("payload") or {}).get("stage_name") == "self_refinement.critique"
    ]
    assert len(gates) == 1
    assert (gates[0].get("payload") or {}).get("verdict") == "PASS"
