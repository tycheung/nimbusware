"""Production evaluator LLM fallback without stub env."""

from __future__ import annotations

from nimbusware_orchestrator.workflow_agent_evaluator import (
    AgentEvaluatorWorkflowBlock,
    agent_evaluator_production_llm_fallback_enabled,
    agent_evaluator_rules_derived_llm_evaluation,
)


def test_production_llm_fallback_enabled_without_stub_env(
    monkeypatch,
) -> None:
    block = AgentEvaluatorWorkflowBlock(enabled=True, llm_evaluation_enabled=True)
    monkeypatch.delenv("NIMBUSWARE_AGENT_EVALUATOR_LLM_STUB", raising=False)
    assert agent_evaluator_production_llm_fallback_enabled(block) is True


def test_rules_derived_llm_evaluation_shape() -> None:
    derived = agent_evaluator_rules_derived_llm_evaluation(
        {"status": "ok", "gaps": ["gap-a"], "score": 0.8},
    )
    assert derived["production_scoring_mode"] == "rules_derived"
    assert derived["gaps"] == ["gap-a"]
