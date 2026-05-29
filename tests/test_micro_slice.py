"""Micro-slice planning and budgets."""

from __future__ import annotations

from pathlib import Path

from hermes_orchestrator.micro_slice import (
    parse_slice_plan,
    validate_diff_budget,
    micro_slice_timeline_summary,
)
from hermes_orchestrator.workflow_micro_slice import parse_micro_slice_workflow_block


def test_parse_slice_plan() -> None:
    plan = parse_slice_plan(
        {
            "slice_id": "s1",
            "rationale": "touch api only",
            "target_paths": ["packages/nimbusware_api/routes/runs.py"],
            "acceptance_criteria": "tests pass",
        },
    )
    assert plan.slice_id == "s1"
    assert plan.target_paths[0].endswith("runs.py")


def test_validate_diff_budget_rejects_large_slice() -> None:
    from hermes_orchestrator.workflow_micro_slice import MicroSliceWorkflowBlock

    cfg = MicroSliceWorkflowBlock(enabled=True, max_files=2, max_loc=50)
    result = validate_diff_budget(
        changed_files=["a.py", "b.py", "c.py"],
        loc_added=10,
        loc_removed=10,
        config=cfg,
    )
    assert not result.ok
    assert "max_files" in result.message


def test_micro_slice_workflow_profile() -> None:
    root = Path(__file__).resolve().parents[1]
    block = parse_micro_slice_workflow_block(root, "micro_slice")
    assert block.enabled is True
    assert block.max_files == 3


def test_micro_slice_timeline_summary() -> None:
    events = [
        {
            "metadata": {"slice_plan": True, "slice_id": "s1"},
        },
        {
            "metadata": {"slice_gate_verdict": "PASS", "slice_id": "s1"},
        },
    ]
    summary = micro_slice_timeline_summary(events)
    assert summary["slice_count_planned"] == 1
    assert summary["slices_completed"] == 1
