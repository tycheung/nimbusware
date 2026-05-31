"""Automatic micro-slice execution via lifecycle verify."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hermes_orchestrator.micro_slice import micro_slice_timeline_summary
from hermes_orchestrator.micro_slice_executor import micro_slice_count_for_run
from hermes_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_env import find_repo_root


@pytest.fixture(autouse=True)
def _single_slice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_MICRO_SLICE_COUNT", "1")


def test_execute_micro_slice_pass_via_orchestrator() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("micro_slice")
    results = orch.execute_micro_slice_pass(run_id, workspace=repo)
    assert len(results) == 1
    rows = store.list_run_events(str(run_id))
    events = [{"metadata": r.get("metadata") or {}} for r in rows]
    summary = micro_slice_timeline_summary(events)
    assert summary["slice_count_planned"] >= 1
    assert summary["slices_completed"] + summary["slices_blocked"] >= 1


def test_writer_verifier_pass_delegates_to_micro_slice() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("micro_slice")
    orch.execute_writer_verifier_pass(run_id, workspace=repo)
    rows = store.list_run_events(str(run_id))
    stage_names = [
        (r.get("payload") or {}).get("stage_name")
        for r in rows
        if r.get("event_type") == "stage.started"
    ]
    assert "slice.plan" in stage_names
    assert "implementation" not in stage_names


def test_micro_slice_count_env() -> None:
    os.environ["HERMES_MICRO_SLICE_COUNT"] = "3"
    try:
        assert micro_slice_count_for_run() == 3
    finally:
        os.environ.pop("HERMES_MICRO_SLICE_COUNT", None)
