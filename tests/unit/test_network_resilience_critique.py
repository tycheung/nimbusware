from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.network_resilience_critique import (
    NETWORK_RESILIENCE_CRITIQUE_STAGE,
    scan_summary_failed,
)
from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.workflow_network_resilience_critique import (
    network_resilience_critique_effective,
    parse_network_resilience_critique_workflow_block,
)


def test_scan_summary_failed() -> None:
    failed, reasons = scan_summary_failed({"http_resilience_exit": 1, "sql_query_budget_exit": 0})
    assert failed
    assert "http_resilience" in reasons


def test_network_resilience_workflow_block() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    block = parse_network_resilience_critique_workflow_block(root, "network_resilience_critique_on")
    assert block.enabled is True
    assert network_resilience_critique_effective(block)


def test_verify_runs_network_resilience_critique(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("network_resilience_critique_on")
    monkeypatch.setattr(
        "nimbusware_orchestrator.pipeline.run_writer_verifier_bundle",
        lambda ws: (0, "ok\n"),
    )
    monkeypatch.setattr(
        "nimbusware_orchestrator.pipeline.run_network_resilience_scan_summary",
        lambda ws: {
            "http_resilience_exit": 0,
            "sql_query_budget_exit": 0,
            "network_resilience_exit": 0,
        },
    )
    orch.execute_writer_verifier_pass(run_id, workspace=repo)
    rows = store.list_run_events(str(run_id))
    assert any(
        (r.get("payload") or {}).get("stage_name") == NETWORK_RESILIENCE_CRITIQUE_STAGE
        for r in rows
        if r.get("event_type") == "stage.started"
    )
