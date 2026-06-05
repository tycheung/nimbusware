from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest

from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_maker.approval import has_plan_approved, pending_slice_from_rows
from nimbusware_maker.intent import build_requirements_artifact
from nimbusware_maker.slice_workflow import (
    apply_pending_slice,
    approve_run_plan,
    prepare_next_pending_slice,
    revert_workspace,
    skip_pending_slice,
)


@pytest.fixture
def maker_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple:
    from nimbusware_env import find_repo_root

    monkeypatch.setenv("NIMBUSWARE_SLICE_IMPLEMENT", "stub")
    monkeypatch.setenv("NIMBUSWARE_SLICE_AUTO_ADVANCE", "0")
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    ws = tmp_path / "project"
    ws.mkdir()
    (ws / "packages/nimbusware_orchestrator/micro_slice.py").parent.mkdir(parents=True, exist_ok=True)
    (ws / "packages/nimbusware_orchestrator/micro_slice.py").write_text("# stub\n", encoding="utf-8")
    (ws / "packages/nimbusware_orchestrator/slice_gate.py").write_text("# stub\n", encoding="utf-8")
    orch, store = make_dev_orchestrator(repo)
    requirements = build_requirements_artifact(business_prompt="Inventory app")
    run_id = orch.create_run(
        "micro_slice",
        requirements=requirements,
        project_id=uuid4(),
        project_name="Demo",
        project_workspace_path=str(ws),
        project_template="attach",
    )
    return orch, store, run_id, ws


def test_plan_approve_and_prepare_pending(maker_run: tuple) -> None:
    orch, store, run_id, _ws = maker_run
    approve_run_plan(orch, run_id)
    rows = store.list_run_events(str(run_id))
    assert has_plan_approved(rows)
    body = prepare_next_pending_slice(orch, run_id)
    assert body["status"] == "awaiting_approval"
    rows = store.list_run_events(str(run_id))
    assert pending_slice_from_rows(rows) is not None


def test_skip_pending_slice(maker_run: tuple) -> None:
    orch, store, run_id, _ws = maker_run
    approve_run_plan(orch, run_id)
    prep = prepare_next_pending_slice(orch, run_id)
    slice_id = prep["pending"]["slice_id"]
    skip_pending_slice(orch, run_id, slice_id)
    rows = store.list_run_events(str(run_id))
    assert pending_slice_from_rows(rows) is None


def test_apply_pending_slice_stub(maker_run: tuple) -> None:
    orch, store, run_id, _ws = maker_run
    approve_run_plan(orch, run_id)
    prep = prepare_next_pending_slice(orch, run_id)
    slice_id = prep["pending"]["slice_id"]
    os.environ["NIMBUSWARE_SKIP_PREFLIGHT"] = "1"
    result = apply_pending_slice(orch, run_id, slice_id)
    assert result["status"] == "applied"
    rows = store.list_run_events(str(run_id))
    assert pending_slice_from_rows(rows) is None


def test_revert_workspace_after_apply(maker_run: tuple) -> None:
    orch, store, run_id, ws = maker_run
    target = ws / "packages/nimbusware_orchestrator/micro_slice.py"
    before = target.read_text(encoding="utf-8")
    approve_run_plan(orch, run_id)
    prep = prepare_next_pending_slice(orch, run_id)
    slice_id = prep["pending"]["slice_id"]
    os.environ["NIMBUSWARE_SKIP_PREFLIGHT"] = "1"
    apply_pending_slice(orch, run_id, slice_id)
    target.write_text("corrupted\n", encoding="utf-8")
    result = revert_workspace(orch, run_id)
    assert result["status"] == "reverted"
    assert target.read_text(encoding="utf-8") == before
