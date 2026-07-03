from __future__ import annotations

from pathlib import Path

from env import find_repo_root
from orchestrator.critique.handlers import (
    performance_scan_tools_failed,
)
from orchestrator.workflow.scan_critique import (
    parse_performance_critique_workflow_block,
    performance_critique_effective,
)


def test_performance_scan_tools_failed() -> None:
    summary = {
        "security_scan_tools": {
            "ruff": 0,
            "bandit": 0,
            "mypy": 0,
            "ruff_perf": 1,
            "n_plus_one_heuristic": 0,
        },
    }
    failed, tools = performance_scan_tools_failed(summary)
    assert failed
    assert "ruff_perf" in tools


def test_performance_critique_workflow_block() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    block = parse_performance_critique_workflow_block(root, "performance_critique_on")
    assert block.enabled is True
    assert performance_critique_effective(block)
