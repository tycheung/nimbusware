from __future__ import annotations

from pathlib import Path

from env import find_repo_root
from orchestrator.campaign.generator import (
    emit_backlog_generated,
    generate_heuristic_backlog,
)
from orchestrator.pipeline import make_dev_orchestrator
from projections.builders.backlog_tree import (
    backlog_tree_from_events,
    campaign_has_backlog,
)


def test_backlog_tree_from_events() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("campaign_micro_slice")
    backlog = generate_heuristic_backlog(str(run_id), max_slices=3)
    emit_backlog_generated(store, run_id, backlog)
    rows = store.list_run_events(str(run_id))
    tree = backlog_tree_from_events(rows)
    assert tree is not None
    assert tree["summary"]["total_slices"] == 3
    assert campaign_has_backlog(rows) is True


def _fullstack_requirements() -> dict:
    return {
        "prompt": "Build a todo app with API and web UI",
        "stack_manifest": {
            "surfaces": ["api", "web"],
            "stacks": {"api": "fastapi_python", "web": "react_vite"},
            "confirmed": True,
        },
    }


def test_campaign_has_backlog_false_without_events() -> None:
    assert campaign_has_backlog([]) is False


def test_backlog_tree_includes_surface_fields() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("campaign_fullstack")
    backlog = generate_heuristic_backlog(
        str(run_id),
        requirements=_fullstack_requirements(),
        max_slices=12,
    )
    emit_backlog_generated(store, run_id, backlog)
    rows = store.list_run_events(str(run_id))
    tree = backlog_tree_from_events(rows)
    assert tree is not None
    surfaces = {
        sl.get("surface_id")
        for epic in tree["epics"]
        for feature in epic["features"]
        for sl in feature["slices"]
        if sl.get("surface_id")
    }
    assert "api" in surfaces
    assert "web" in surfaces
