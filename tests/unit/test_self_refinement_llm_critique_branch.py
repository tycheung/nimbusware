from __future__ import annotations

import pytest

from orchestrator.workflow_self_refinement import (
    SelfRefinementWorkflowBlock,
    self_refinement_llm_critique_branch_effective,
)


def test_self_refinement_llm_critique_branch_yaml_only() -> None:
    block = SelfRefinementWorkflowBlock(enabled=True, llm_critique_enabled=True)
    assert self_refinement_llm_critique_branch_effective(block) is True


def test_self_refinement_llm_critique_branch_kill_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    block = SelfRefinementWorkflowBlock(enabled=True, llm_critique_enabled=True)
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "0")
    assert self_refinement_llm_critique_branch_effective(block) is False
