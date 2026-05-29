"""PZ-8: Phase 3 critic stages enabled on nimbusware_production."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from hermes_orchestrator.network_resilience_critique import NETWORK_RESILIENCE_CRITIQUE_STAGE
from hermes_orchestrator.refactor_stage import REFACTOR_CRITIQUE_STAGE
from hermes_orchestrator.workflow_refactor import (
    parse_refactor_workflow_block,
    refactor_stage_effective,
)
from hermes_orchestrator.performance_critique import PERFORMANCE_CRITIQUE_STAGE
from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.security_critique import SECURITY_CRITIQUE_STAGE
from hermes_orchestrator.workflow_network_resilience_critique import (
    network_resilience_critique_effective,
    parse_network_resilience_critique_workflow_block,
)
from hermes_orchestrator.workflow_performance_critique import (
    parse_performance_critique_workflow_block,
    performance_critique_effective,
)
from hermes_orchestrator.workflow_security_critique import (
    parse_security_critique_workflow_block,
    security_critique_effective,
)


def test_nimbusware_production_yaml_enables_p3_blocks() -> None:
    root = Path(__file__).resolve().parents[1]
    sec = parse_security_critique_workflow_block(root, "nimbusware_production")
    perf = parse_performance_critique_workflow_block(root, "nimbusware_production")
    net = parse_network_resilience_critique_workflow_block(root, "nimbusware_production")
    assert security_critique_effective(sec)
    assert performance_critique_effective(perf)
    assert network_resilience_critique_effective(net)


def test_nimbusware_production_verify_emits_p3_stages(monkeypatch: pytest.MonkeyPatch) -> None:
    root = Path(__file__).resolve().parents[1]
    orch, store = make_dev_orchestrator(root)
    run_id = orch.create_run("nimbusware_production")

    monkeypatch.setattr(
        "hermes_orchestrator.pipeline.run_writer_verifier_bundle",
        lambda ws: (0, "ok\n"),
    )
    monkeypatch.setattr(
        "hermes_orchestrator.pipeline.run_security_scan_summary",
        lambda ws: {
            "security_scan_tools": {
                "ruff": 0,
                "bandit": 0,
                "mypy": 0,
                "ruff_perf": 0,
                "n_plus_one_heuristic": 0,
                "semgrep": 0,
                "sql_profiler": 0,
            },
            "security_scan_exit": 0,
        },
    )
    monkeypatch.setattr(
        "hermes_orchestrator.pipeline.run_network_resilience_scan_summary",
        lambda ws: {
            "network_resilience_exit": 0,
            "http_resilience_exit": 0,
            "sql_query_budget_exit": 0,
        },
    )

    with patch.dict(
        os.environ,
        {"HERMES_STUB_IMPLEMENTATION_CRITICS": "0"},
        clear=False,
    ):
        orch.execute_writer_verifier_pass(run_id, workspace=root)

    stage_names = [
        (r.get("payload") or {}).get("stage_name")
        for r in store.list_run_events(str(run_id))
        if r.get("event_type") == "stage.started"
    ]
    assert SECURITY_CRITIQUE_STAGE in stage_names
    assert PERFORMANCE_CRITIQUE_STAGE in stage_names
    assert NETWORK_RESILIENCE_CRITIQUE_STAGE in stage_names
    assert REFACTOR_CRITIQUE_STAGE in stage_names
