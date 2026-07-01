from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    StagePassedEvent,
    StagePassedPayload,
    StageStartedEvent,
    StageStartedPayload,
)
from agent_core.slice_plan import SlicePlan
from nimbusware_orchestrator.micro_slice_run_context import micro_slice_effective_from_rows
from nimbusware_orchestrator.workflow_blocks_simple import (
    MicroSliceWorkflowBlock,
    parse_micro_slice_workflow_block,
)

if TYPE_CHECKING:
    from nimbusware_orchestrator.pipeline import RunOrchestrator


def _launch_test_enabled(rows: list[dict[str, Any]]) -> bool:
    from nimbusware_orchestrator.dev_env_policy import launch_test_enabled

    return launch_test_enabled(rows)


def _active_enforcement(rows: list[dict[str, Any]]) -> Any:
    from nimbusware_orchestrator.enforcement_pipeline import active_enforcement_profile

    return active_enforcement_profile(rows)


def _resolve_slice_block(orch: RunOrchestrator, run_id: UUID) -> MicroSliceWorkflowBlock:
    from nimbusware_orchestrator.integrator_gate import workflow_profile_from_run_created_rows

    rows = orch._store.list_run_events(str(run_id))
    wf = workflow_profile_from_run_created_rows(rows)
    block = parse_micro_slice_workflow_block(
        orch.repo_root,
        wf or "micro_slice",
        config_materializer=orch.config_materializer,
    )
    ms = micro_slice_effective_from_rows(rows)
    if not ms:
        return block
    max_files = int(ms.get("max_files", block.max_files))
    max_loc = int(ms.get("max_loc", block.max_loc))
    from nimbusware_env.env_flags import env_str
    from nimbusware_iam.context import get_auth_context
    from nimbusware_orchestrator.fleet_slice_caps import clamp_slice_budget

    ctx = get_auth_context()
    max_files, max_loc, _ = clamp_slice_budget(
        max_files,
        max_loc,
        tenant_slug=ctx.tenant_slug if ctx is not None else None,
        setup_bundle=env_str("NIMBUSWARE_SETUP_BUNDLE").strip() or "default",
    )
    return MicroSliceWorkflowBlock(
        enabled=True,
        max_files=max_files,
        max_loc=max_loc,
        allowed_globs=block.allowed_globs,
        e2e_enabled=bool(ms.get("e2e_enabled", block.e2e_enabled)),
        e2e_command=block.e2e_command,
    )


def resolve_slice_block_for_plan(
    orch: RunOrchestrator,
    run_id: UUID,
    plan: SlicePlan | None,
) -> MicroSliceWorkflowBlock:
    from nimbusware_orchestrator.slice_interjection import _project_from_run_rows
    from nimbusware_orchestrator.stack_diff_budget import merge_stack_diff_budget

    block = _resolve_slice_block(orch, run_id)
    if plan is None:
        return block
    rows = orch._store.list_run_events(str(run_id))
    return merge_stack_diff_budget(
        block,
        plan,
        repo_root=orch.repo_root,
        manifest=_project_from_run_rows(rows),
    )


def _emit_slice_stage(
    orch: RunOrchestrator,
    run_id: UUID,
    stage_name: str,
    *,
    metadata: dict[str, Any] | None = None,
    duration_ms: int = 0,
) -> None:
    now = datetime.now(timezone.utc)
    orch._store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            metadata=metadata or {},
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    orch._store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=metadata or {},
            payload=StagePassedPayload(stage_name=stage_name, duration_ms=duration_ms),
        ),
    )
