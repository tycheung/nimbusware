"""Performance Critic stage."""

from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.performance_critique import (
    PERFORMANCE_CRITIQUE_STAGE,
    performance_scan_tools_failed,
)
from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.workflow_performance_critique import (
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


def test_verify_pass_runs_performance_critique(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("performance_critique_on")
    monkeypatch.setattr(
        "nimbusware_orchestrator.pipeline.run_writer_verifier_bundle",
        lambda ws: (0, "ok\n"),
    )
    orch.execute_writer_verifier_pass(run_id, workspace=repo)
    rows = store.list_run_events(str(run_id))
    assert any(
        (r.get("payload") or {}).get("stage_name") == PERFORMANCE_CRITIQUE_STAGE
        for r in rows
        if r.get("event_type") == "stage.started"
    )
