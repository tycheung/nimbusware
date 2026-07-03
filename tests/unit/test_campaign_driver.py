from __future__ import annotations

from pathlib import Path

import pytest

from env import find_repo_root
from orchestrator.backlog_generator import (
    generate_heuristic_backlog,
    has_backlog_event,
)
from orchestrator.campaign import campaign_policy_from_workflow, emit_campaign_created
from orchestrator.campaign_driver import campaign_driver_tick
from orchestrator.campaign_slice_selector import select_next_slice
from orchestrator.pipeline import make_dev_orchestrator


def test_generate_heuristic_backlog_has_bounded_slices() -> None:
    backlog = generate_heuristic_backlog(
        "run-1",
        requirements={"business_prompt": "Build a CRM with contacts"},
        max_slices=10,
    )
    assert backlog.metadata.total_slices_planned == 5
    selected = select_next_slice(backlog)
    assert selected is not None
    assert selected.slice.slice_id == "slice-001"


@pytest.fixture(autouse=True)
def _single_stub_slice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_MICRO_SLICE_COUNT", "1")


def test_campaign_driver_tick_generates_backlog() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("campaign_micro_slice")
    policy = campaign_policy_from_workflow(repo, "campaign_micro_slice")
    emit_campaign_created(store, run_id, workflow_profile="campaign_micro_slice", policy=policy)
    rows = store.list_run_events(str(run_id))
    assert has_backlog_event(rows) is False
    result = campaign_driver_tick(orch, run_id, workspace=repo)
    rows = store.list_run_events(str(run_id))
    assert has_backlog_event(rows) is True
    assert "slice.queued" in [r.get("event_type") for r in rows]
    assert result.slices_completed >= 0
