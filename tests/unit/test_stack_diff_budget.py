from __future__ import annotations

from agent_core.slice_plan import SlicePlan
from orchestrator.stack_diff_budget import merge_stack_diff_budget
from orchestrator.workflow_blocks_simple import MicroSliceWorkflowBlock


def test_merge_stack_diff_budget_tightens_web_stack() -> None:
    block = MicroSliceWorkflowBlock(enabled=True, max_files=8, max_loc=400)
    plan = SlicePlan(
        slice_id="s1",
        rationale="web ui",
        target_paths=("frontend/App.tsx",),
        surface_id="web",
        stack_id="react_vite",
    )
    merged = merge_stack_diff_budget(block, plan)
    assert merged.max_files == 4
    assert merged.max_loc == 160


def test_merge_stack_diff_budget_resolves_stack_from_manifest() -> None:
    block = MicroSliceWorkflowBlock(enabled=True, max_files=10, max_loc=500)
    plan = SlicePlan(
        slice_id="s2",
        rationale="api",
        target_paths=("backend/main.py",),
        surface_id="api",
    )
    manifest = {"stacks": {"api": "fastapi_python"}}
    merged = merge_stack_diff_budget(block, plan, manifest=manifest)
    assert merged.max_files == 5
    assert merged.max_loc == 200


def test_merge_stack_diff_budget_keeps_block_when_no_stack() -> None:
    block = MicroSliceWorkflowBlock(enabled=True, max_files=3, max_loc=120)
    plan = SlicePlan("s3", "r", ("a.py",))
    merged = merge_stack_diff_budget(block, plan)
    assert merged.max_files == 3
    assert merged.max_loc == 120
