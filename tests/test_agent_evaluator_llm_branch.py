"""Agent evaluator LLM branch without mandatory HERMES_USE_LLM (§14 #15)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_orchestrator.workflow_agent_evaluator import (
    AgentEvaluatorWorkflowBlock,
    agent_evaluator_llm_branch_effective,
    persona_coverage_critique_llm_branch_effective,
)

ROOT = Path(__file__).resolve().parents[1]


def test_agent_evaluator_llm_branch_yaml_only() -> None:
    block = AgentEvaluatorWorkflowBlock(enabled=True, llm_evaluation_enabled=True)
    assert agent_evaluator_llm_branch_effective(block) is True


def test_agent_evaluator_llm_branch_kill_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    block = AgentEvaluatorWorkflowBlock(enabled=True, llm_evaluation_enabled=True)
    monkeypatch.setenv("HERMES_USE_LLM", "0")
    assert agent_evaluator_llm_branch_effective(block) is False


def test_persona_coverage_llm_branch_yaml_only() -> None:
    from hermes_orchestrator.workflow_agent_evaluator import PersonaCoverageCritiqueBlock

    block = AgentEvaluatorWorkflowBlock(
        enabled=True,
        persona_coverage_critique=PersonaCoverageCritiqueBlock(
            enabled=True,
            llm_enabled=True,
        ),
    )
    assert persona_coverage_critique_llm_branch_effective(block) is True
