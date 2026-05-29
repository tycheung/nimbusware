"""Persona Coverage Critic gate (plan §14 #15)."""

from __future__ import annotations

import os
from unittest.mock import patch

from agent_core.models import EventType, Verdict
from hermes_orchestrator.pipeline import make_dev_orchestrator


@patch.dict(os.environ, {"HERMES_AGENT_EVALUATOR": "1"}, clear=False)
@patch("hermes_orchestrator.pipeline.run_writer_verifier_bundle", return_value=(0, "ok"))
def test_missing_persona_assignment_fails_coverage_gate(_mock: object) -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("agent_evaluator_default_on")
    orch.execute_writer_verifier_pass(rid)
    rows = mem.list_run_events(str(rid))
    critic_rows = [r for r in rows if r.get("event_type") == EventType.CRITIC_VERDICT_EMITTED.value]
    assert len(critic_rows) >= 2
    gate = next(
        r
        for r in rows
        if r.get("event_type") == EventType.GATE_DECISION_EMITTED.value
        and (r.get("payload") or {}).get("stage_name") == "agent_evaluator.critique"
    )
    assert (gate.get("payload") or {}).get("verdict") == Verdict.FAIL.value
    assert (gate.get("payload") or {}).get("failing_critics")


@patch.dict(os.environ, {"HERMES_AGENT_EVALUATOR": "1"}, clear=False)
@patch("hermes_orchestrator.pipeline.run_writer_verifier_bundle", return_value=(0, "ok"))
def test_persona_coverage_kill_switch_disables_panel(_mock: object) -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("agent_evaluator_on")
    with patch.dict(os.environ, {"HERMES_PERSONA_COVERAGE_CRITIQUE": "0"}, clear=False):
        orch.execute_writer_verifier_pass(rid)
    rows = mem.list_run_events(str(rid))
    assert not any(
        (r.get("payload") or {}).get("stage_name") == "agent_evaluator.critique"
        for r in rows
        if r.get("event_type") == EventType.GATE_DECISION_EMITTED.value
    )


@patch.dict(os.environ, {"HERMES_AGENT_EVALUATOR": "1"}, clear=False)
@patch("hermes_orchestrator.pipeline.run_writer_verifier_bundle", return_value=(0, "ok"))
def test_valid_assignment_passes_coverage_gate(_mock: object) -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run(
        "agent_evaluator_on",
        business_area_persona_id="commerce",
        development_role_persona_id="backend_engineer",
    )
    orch.execute_writer_verifier_pass(rid)
    gate = next(
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == EventType.GATE_DECISION_EMITTED.value
        and (r.get("payload") or {}).get("stage_name") == "agent_evaluator.critique"
    )
    assert (gate.get("payload") or {}).get("verdict") == Verdict.PASS.value
