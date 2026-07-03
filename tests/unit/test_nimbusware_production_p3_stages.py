from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from env import find_repo_root
from orchestrator.pipeline import make_dev_orchestrator
from orchestrator.refactor_stage import REFACTOR_CRITIQUE_STAGE
from orchestrator.scan_critique_handlers import (
    NETWORK_RESILIENCE_CRITIQUE_STAGE,
    PERFORMANCE_CRITIQUE_STAGE,
    SECURITY_CRITIQUE_STAGE,
)
from orchestrator.workflow_scan_critique import (
    network_resilience_critique_effective,
    parse_network_resilience_critique_workflow_block,
    parse_performance_critique_workflow_block,
    parse_security_critique_workflow_block,
    performance_critique_effective,
    security_critique_effective,
)


def test_nimbusware_production_yaml_enables_p3_blocks() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    sec = parse_security_critique_workflow_block(root, "nimbusware_production")
    perf = parse_performance_critique_workflow_block(root, "nimbusware_production")
    net = parse_network_resilience_critique_workflow_block(root, "nimbusware_production")
    assert security_critique_effective(sec)
    assert performance_critique_effective(perf)
    assert network_resilience_critique_effective(net)


def test_nimbusware_production_verify_runs_micro_slice_stages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(root)
    run_id = orch.create_run("nimbusware_production")

    monkeypatch.setenv("NIMBUSWARE_SLICE_IMPLEMENT", "stub")
    with patch.dict(
        os.environ,
        {"NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS": "0", "NIMBUSWARE_SLICE_P3_EVIDENCE": "0"},
        clear=False,
    ):
        orch.execute_writer_verifier_pass(run_id, workspace=root)

    stage_names = [
        (r.get("payload") or {}).get("stage_name")
        for r in store.list_run_events(str(run_id))
        if r.get("event_type") == "stage.started"
    ]
    assert "slice.plan" in stage_names
    assert "slice.implement" in stage_names
    assert "slice.verify" in stage_names
    assert SECURITY_CRITIQUE_STAGE not in stage_names
    assert PERFORMANCE_CRITIQUE_STAGE not in stage_names
    assert NETWORK_RESILIENCE_CRITIQUE_STAGE not in stage_names
    assert REFACTOR_CRITIQUE_STAGE not in stage_names
