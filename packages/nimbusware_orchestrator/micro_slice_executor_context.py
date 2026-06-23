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
from nimbusware_orchestrator.micro_slice_run_context import micro_slice_effective_from_rows
from nimbusware_orchestrator.workflow_micro_slice import (
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
    from nimbusware_orchestrator.workflow_micro_slice import parse_micro_slice_workflow_block

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
    return MicroSliceWorkflowBlock(
        enabled=True,
        max_files=int(ms.get("max_files", block.max_files)),
        max_loc=int(ms.get("max_loc", block.max_loc)),
        allowed_globs=block.allowed_globs,
        e2e_enabled=bool(ms.get("e2e_enabled", block.e2e_enabled)),
        e2e_command=block.e2e_command,
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


