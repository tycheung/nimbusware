from __future__ import annotations

from pathlib import Path

from env import find_repo_root
from orchestrator.workflow.refactor import (
    parse_refactor_workflow_block,
    refactor_stage_effective,
)


def test_refactor_workflow_block() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    block = parse_refactor_workflow_block(root, "refactor_on")
    assert block.enabled is True
    assert refactor_stage_effective(block)
    prod = parse_refactor_workflow_block(root, "nimbusware_production")
    assert prod.stub_only is False
    assert prod.orphan_gate_max == 15
