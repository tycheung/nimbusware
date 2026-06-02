"""Diff-aware micro-slice replanning."""

from __future__ import annotations

from pathlib import Path

from hermes_orchestrator.micro_slice import parse_slice_plan, validate_diff_budget
from hermes_orchestrator.slice_diff import (
    check_slice_diff_budget,
    collect_slice_diff_stats,
    subdivide_slice_plan,
)
from hermes_orchestrator.workflow_micro_slice import MicroSliceWorkflowBlock
from nimbusware_env import find_repo_root


def test_subdivide_slice_plan_reduces_file_count() -> None:
    plan = parse_slice_plan(
        {
            "slice_id": "s1",
            "target_paths": ["a.py", "b.py", "c.py", "d.py"],
        },
    )
    cfg = MicroSliceWorkflowBlock(enabled=True, max_files=2, max_loc=500)
    from hermes_orchestrator.micro_slice import DiffBudgetResult

    budget = DiffBudgetResult(
        ok=False,
        file_count=4,
        loc_count=0,
        message="slice exceeds max_files (2): 4 files",
    )
    stats = collect_slice_diff_stats(
        find_repo_root(start=Path(__file__).resolve().parents[1]), plan
    )
    sub = subdivide_slice_plan(
        plan,
        budget=budget,
        config=cfg,
        stats=stats,
        replan_attempt=1,
    )
    assert sub is not None
    assert len(sub.target_paths) == 2
    assert sub.slice_id.endswith("-r1")


def test_collect_slice_diff_stats_plan_estimate() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    plan = parse_slice_plan(
        {
            "slice_id": "s1",
            "target_paths": ["packages/hermes_orchestrator/micro_slice.py"],
        },
    )
    stats = collect_slice_diff_stats(root, plan)
    assert stats.loc_added + stats.loc_removed >= 0
    cfg = MicroSliceWorkflowBlock(enabled=True, max_files=3, max_loc=1)
    budget = check_slice_diff_budget(stats, cfg)
    if stats.loc_added + stats.loc_removed <= 1:
        cfg_tight_files = MicroSliceWorkflowBlock(enabled=True, max_files=0, max_loc=999)
        budget = check_slice_diff_budget(stats, cfg_tight_files)
    assert not budget.ok


def test_validate_diff_budget_unchanged() -> None:
    cfg = MicroSliceWorkflowBlock(enabled=True, max_files=2, max_loc=10)
    ok = validate_diff_budget(
        changed_files=["a.py"],
        loc_added=5,
        loc_removed=5,
        config=cfg,
    )
    assert ok.ok
