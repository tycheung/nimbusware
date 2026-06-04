"""B1 promotion: Integration Adapter Writer target I/O."""

from __future__ import annotations

from pathlib import Path

from hermes_orchestrator.integration_adapter_scaffold import write_integration_adapter_scaffold
from hermes_orchestrator.integration_adapter_writer_stage import INTEGRATION_ADAPTER_WRITER_STAGE
from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.workflow_integration_adapter_writer import (
    IntegrationAdapterWriterWorkflowBlock,
)
from nimbusware_env import find_repo_root


def test_target_adapter_integration_writes_state_and_sync(tmp_path: Path) -> None:
    from uuid import uuid4

    rid = uuid4()
    block = IntegrationAdapterWriterWorkflowBlock(
        enabled=True,
        target_adapter_kind="api_bridge",
        stub_only=False,
    )
    out = write_integration_adapter_scaffold(tmp_path, rid, block)
    assert out["adapter_generation_status"] == "target_integrated"
    assert out["target_integration_status"] == "integrated"
    assert out["target_connected"] is True
    state = tmp_path / ".hermes" / "integration_adapter_writer" / str(rid) / "target_state.json"
    assert state.is_file()


def test_pipeline_live_iaw_target_integrated() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, mem = make_dev_orchestrator(repo_root=root)
    rid = orch.create_run("integration_adapter_writer_live")
    orch._maybe_emit_integration_adapter_writer_stage(rid)  # noqa: SLF001
    row = next(
        r
        for r in mem.list_run_events(str(rid))
        if (r.get("payload") or {}).get("stage_name") == INTEGRATION_ADAPTER_WRITER_STAGE
    )
    iaw = (row.get("metadata") or {}).get("integration_adapter_writer") or {}
    assert iaw.get("scaffold_status") == "target_integrated"
    assert iaw.get("target_integration_status") == "integrated"
    rel = iaw["workspace_manifest_path"]
    state = root / Path(rel).parent / "target_state.json"
    assert state.is_file()
