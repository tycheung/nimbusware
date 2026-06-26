from __future__ import annotations

from pathlib import Path

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.scan_critique_handlers import (
    scan_summary_failed,
)
from nimbusware_orchestrator.workflow_scan_critique import (
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
