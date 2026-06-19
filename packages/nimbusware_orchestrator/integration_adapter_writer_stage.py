from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, StageStartedEvent, StageStartedPayload
from nimbusware_orchestrator.workflow_integration_adapter_writer import (
    IntegrationAdapterWriterWorkflowBlock,
    integration_adapter_writer_effective,
    parse_integration_adapter_writer_workflow_block,
)
from nimbusware_store.protocol import EventStore

INTEGRATION_ADAPTER_WRITER_STAGE = "integration_adapter_writer"


def integration_adapter_writer_stage_would_emit(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> bool:
    block = parse_integration_adapter_writer_workflow_block(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    return integration_adapter_writer_effective(block)


def emit_stub_integration_adapter_writer_stage(
    store: EventStore,
    *,
    run_id: UUID,
    block: IntegrationAdapterWriterWorkflowBlock,
) -> None:
    """Append scaffold ``stage.started``; no adapter I/O (live path deferred)."""
    meta = {
        "integration_adapter_writer": {
            "stub_only": block.stub_only,
            "target_adapter_kind": block.target_adapter_kind,
            "scaffold_status": "stub_only",
        },
    }
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=meta,
            payload=StageStartedPayload(
                stage_name=INTEGRATION_ADAPTER_WRITER_STAGE,
                attempt=1,
            ),
        ),
    )


def record_live_adapter_workspace(
    repo_root: Path,
    run_id: UUID,
    block: IntegrationAdapterWriterWorkflowBlock,
) -> dict[str, Any]:
    """Persist adapter scaffold (manifest + module + README) for the run."""
    from nimbusware_orchestrator.integration_adapter_scaffold import (
        write_integration_adapter_scaffold,
    )

    return write_integration_adapter_scaffold(repo_root, run_id, block)


def emit_live_integration_adapter_writer_stage(
    store: EventStore,
    *,
    run_id: UUID,
    block: IntegrationAdapterWriterWorkflowBlock,
    repo_root: Path | None = None,
) -> None:
    """Append live-path ``stage.started`` with workspace manifest I/O when ``repo_root`` set."""
    iaw: dict[str, Any] = {
        "stub_only": block.stub_only,
        "target_adapter_kind": block.target_adapter_kind,
        "scaffold_status": "live_adapter_recorded",
    }
    if repo_root is not None:
        workspace = record_live_adapter_workspace(repo_root, run_id, block)
        iaw.update(workspace)
        if workspace.get("adapter_generation_status") == "target_integrated":
            iaw["scaffold_status"] = "target_integrated"
    meta = {
        "integration_adapter_writer": iaw,
    }
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=meta,
            payload=StageStartedPayload(
                stage_name=INTEGRATION_ADAPTER_WRITER_STAGE,
                attempt=1,
            ),
        ),
    )
