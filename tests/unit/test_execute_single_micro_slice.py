from __future__ import annotations

from pathlib import Path

import pytest

from env import find_repo_root
from orchestrator.micro_slice import parse_slice_plan
from orchestrator.micro_slice_executor import (
    execute_micro_slice_pass,
    execute_single_micro_slice,
)
from orchestrator.pipeline import make_dev_orchestrator


@pytest.fixture(autouse=True)
def _single_slice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_MICRO_SLICE_COUNT", "1")


def test_execute_single_micro_slice_matches_batch_first_slice() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, _store = make_dev_orchestrator(repo)
    run_id = orch.create_run("micro_slice")
    batch = execute_micro_slice_pass(orch, run_id, workspace=repo)
    assert len(batch) == 1

    orch2, _ = make_dev_orchestrator(repo)
    run_id2 = orch2.create_run("micro_slice")
    single = execute_single_micro_slice(orch2, run_id2, slice_index=1, workspace=repo)
    assert single.passed == batch[0].passed


def test_execute_single_micro_slice_accepts_explicit_plan() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, _store = make_dev_orchestrator(repo)
    run_id = orch.create_run("micro_slice")
    plan = parse_slice_plan(
        {
            "slice_id": "custom-001",
            "target_paths": ["packages/orchestrator/micro_slice.py"],
            "acceptance_criteria": "exists",
        },
    )
    gate = execute_single_micro_slice(
        orch,
        run_id,
        slice_index=1,
        workspace=repo,
        plan=plan,
        backlog_slice_id="backlog-slice-001",
    )
    assert gate.slice_id == "custom-001"
