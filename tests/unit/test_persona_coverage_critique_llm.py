from __future__ import annotations

import os
from unittest.mock import patch

from nimbusware_orchestrator.pipeline import make_dev_orchestrator


@patch.dict(
    os.environ,
    {
        "NIMBUSWARE_AGENT_EVALUATOR": "1",
        "NIMBUSWARE_PERSONA_COVERAGE_CRITIQUE": "1",
        "NIMBUSWARE_PERSONA_COVERAGE_CRITIQUE_LLM": "1",
        "NIMBUSWARE_USE_LLM": "1",
    },
    clear=False,
)
def test_persona_coverage_llm_branch_emits_gate() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("agent_evaluator_coverage_llm_on")
    with patch(
        "nimbusware_orchestrator.pipeline.run_writer_verifier_bundle", return_value=(0, "ok")
    ):
        with patch.object(orch, "_selected_model_for_run", return_value="m"):
            with patch(
                "nimbusware_orchestrator.persona_coverage_critique.ollama_chat_json",
                return_value={"status": "invalid", "gaps": ["x"], "summary": "coverage gap"},
            ):
                orch.execute_writer_verifier_pass(rid)
    gates = [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == "gate.decision.emitted"
        and (r.get("payload") or {}).get("stage_name") == "agent_evaluator.critique"
    ]
    assert gates
