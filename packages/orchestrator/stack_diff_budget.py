from __future__ import annotations

from pathlib import Path

from agent_core.slice_plan import SlicePlan
from env import find_repo_root
from orchestrator.stack_catalog import load_stack_catalog, stack_for_surface
from orchestrator.workflow_blocks_simple import MicroSliceWorkflowBlock


def merge_stack_diff_budget(
    block: MicroSliceWorkflowBlock,
    plan: SlicePlan,
    *,
    repo_root: Path | None = None,
    manifest: dict | None = None,
) -> MicroSliceWorkflowBlock:
    root = repo_root or find_repo_root()
    stack_id = str(plan.stack_id or "").strip()
    stack = load_stack_catalog(root).get(stack_id) if stack_id else None
    if stack is None and manifest is not None and plan.surface_id:
        stack = stack_for_surface(manifest, str(plan.surface_id), repo_root=root)
    if stack is None:
        return block
    if stack.max_files is None and stack.max_loc is None:
        return block
    max_files = (
        min(block.max_files, stack.max_files) if stack.max_files is not None else block.max_files
    )
    max_loc = min(block.max_loc, stack.max_loc) if stack.max_loc is not None else block.max_loc
    globs = stack.allowed_globs if stack.allowed_globs else block.allowed_globs
    return MicroSliceWorkflowBlock(
        enabled=block.enabled,
        max_files=max(1, max_files),
        max_loc=max(1, max_loc),
        allowed_globs=globs,
        e2e_enabled=block.e2e_enabled,
        e2e_command=block.e2e_command,
    )
