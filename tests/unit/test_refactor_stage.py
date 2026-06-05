"""Refactorer + refactor critique."""

from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.refactor_stage import REFACTOR_CRITIQUE_STAGE, REFACTOR_STAGE
from nimbusware_orchestrator.workflow_refactor import (
    parse_refactor_workflow_block,
    refactor_stage_effective,
)
from nimbusware_env import find_repo_root


def test_refactor_workflow_block() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    block = parse_refactor_workflow_block(root, "refactor_on")
    assert block.enabled is True
    assert refactor_stage_effective(block)


def test_verify_runs_refactor_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("refactor_on")
    monkeypatch.setattr(
        "nimbusware_orchestrator.pipeline.run_writer_verifier_bundle",
        lambda ws: (0, "ok\n"),
    )
    orch.execute_writer_verifier_pass(run_id, workspace=repo)
    rows = store.list_run_events(str(run_id))
    stage_names = [
        (r.get("payload") or {}).get("stage_name")
        for r in rows
        if r.get("event_type") == "stage.started"
    ]
    assert REFACTOR_STAGE in stage_names
    assert REFACTOR_CRITIQUE_STAGE in stage_names


def test_refactor_gate_fail_skips_implementation_critique(monkeypatch: pytest.MonkeyPatch) -> None:
    from nimbusware_orchestrator.llm_plan import IMPLEMENTATION_CRITIQUE_STAGE

    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("refactor_on")
    monkeypatch.setattr(
        "nimbusware_orchestrator.pipeline.run_writer_verifier_bundle",
        lambda ws: (0, "ok\n"),
    )
    monkeypatch.setenv("NIMBUSWARE_REFACTOR_FORCE_FAIL", "1")
    orch.execute_writer_verifier_pass(run_id, workspace=repo)
    rows = store.list_run_events(str(run_id))
    assert REFACTOR_CRITIQUE_STAGE in [
        (r.get("payload") or {}).get("stage_name")
        for r in rows
        if r.get("event_type") == "stage.started"
    ]
    assert IMPLEMENTATION_CRITIQUE_STAGE not in [
        (r.get("payload") or {}).get("stage_name")
        for r in rows
        if r.get("event_type") == "stage.started"
    ]
