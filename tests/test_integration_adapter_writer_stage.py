"""Integration Adapter Writer stub pipeline stage (§14 #13)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_core.models import EventType
from hermes_orchestrator.integration_adapter_writer_stage import (
    INTEGRATION_ADAPTER_WRITER_STAGE,
    emit_live_integration_adapter_writer_stage,
    emit_stub_integration_adapter_writer_stage,
    integration_adapter_writer_stage_would_emit,
)
from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.workflow_integration_adapter_writer import (
    IntegrationAdapterWriterWorkflowBlock,
)


def _write_profile(tmp_path: Path, name: str, body: str) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / f"{name}.yaml").write_text(body, encoding="utf-8")


def test_integration_adapter_writer_stage_would_emit_stub_only(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "adapter_on",
        """version: 1
integration_adapter_writer:
  enabled: true
  stub_only: true
""",
    )
    assert integration_adapter_writer_stage_would_emit(tmp_path, "adapter_on") is True


def test_integration_adapter_writer_stage_would_emit_live(
    tmp_path: Path,
) -> None:
    _write_profile(
        tmp_path,
        "adapter_live",
        """version: 1
integration_adapter_writer:
  enabled: true
  stub_only: false
""",
    )
    assert integration_adapter_writer_stage_would_emit(tmp_path, "adapter_live") is True


def test_pipeline_emits_stub_stage() -> None:
    from pathlib import Path as _Path

    root = _Path(__file__).resolve().parents[1]
    orch, mem = make_dev_orchestrator(repo_root=root)
    rid = orch.create_run("integration_adapter_writer_on")
    orch._maybe_emit_integration_adapter_writer_stage(rid)  # noqa: SLF001
    evs = mem.list_run_events(str(rid))
    assert any(
        r["event_type"] == EventType.STAGE_STARTED.value
        and (r.get("payload") or {}).get("stage_name") == INTEGRATION_ADAPTER_WRITER_STAGE
        for r in evs
    )


def test_explainer_would_emit_stage_started(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HERMES_DATABASE_URL", raising=False)
    from hermes_console.integration_adapter_writer_explainer import (
        integration_adapter_writer_workflow_explainer_operator_metrics,
        integration_adapter_writer_workflow_explainer_payload,
    )

    _write_profile(
        tmp_path,
        "adapter_on",
        "version: 1\nintegration_adapter_writer:\n  enabled: true\n  stub_only: true\n",
    )
    payload = integration_adapter_writer_workflow_explainer_payload(tmp_path, "adapter_on")
    assert payload["would_emit_stage_started"] is True
    m = integration_adapter_writer_workflow_explainer_operator_metrics(payload)
    assert m["would_emit_stage_started"] is True


def test_emit_live_integration_adapter_writer_stage_direct() -> None:
    from uuid import uuid4

    from hermes_store.memory import InMemoryEventStore

    store = InMemoryEventStore()
    rid = uuid4()
    block = IntegrationAdapterWriterWorkflowBlock(
        enabled=True,
        target_adapter_kind="api_bridge",
        stub_only=False,
    )
    emit_live_integration_adapter_writer_stage(
        store,
        run_id=rid,
        block=block,
        repo_root=Path(__file__).resolve().parents[1],
    )
    evs = store.list_run_events(str(rid))
    row = next(
        r
        for r in evs
        if (r.get("payload") or {}).get("stage_name") == INTEGRATION_ADAPTER_WRITER_STAGE
    )
    meta = row.get("metadata") or {}
    iaw = meta.get("integration_adapter_writer") or {}
    assert iaw.get("scaffold_status") == "target_integrated"
    assert iaw.get("stub_only") is False
    assert iaw.get("adapter_generation_status") == "target_integrated"
    assert iaw.get("workspace_manifest_path")
    assert iaw.get("adapter_module_path")


def test_pipeline_emits_live_stage() -> None:
    from pathlib import Path as _Path

    root = _Path(__file__).resolve().parents[1]
    orch, mem = make_dev_orchestrator(repo_root=root)
    rid = orch.create_run("integration_adapter_writer_live")
    orch._maybe_emit_integration_adapter_writer_stage(rid)  # noqa: SLF001
    evs = mem.list_run_events(str(rid))
    row = next(
        r
        for r in evs
        if (r.get("payload") or {}).get("stage_name") == INTEGRATION_ADAPTER_WRITER_STAGE
    )
    iaw = (row.get("metadata") or {}).get("integration_adapter_writer") or {}
    assert iaw.get("scaffold_status") == "target_integrated"
    assert iaw.get("adapter_generation_status") == "target_integrated"
    manifest = root / iaw["workspace_manifest_path"]
    assert manifest.is_file()
    module = root / iaw["adapter_module_path"]
    assert module.is_file()
    readme = root / iaw["adapter_readme_path"]
    assert readme.is_file()


def test_explainer_live_path_payload_and_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HERMES_DATABASE_URL", raising=False)
    from hermes_console.integration_adapter_writer_explainer import (
        integration_adapter_writer_workflow_explainer_operator_metrics,
        integration_adapter_writer_workflow_explainer_operator_metrics_caption,
        integration_adapter_writer_workflow_explainer_payload,
    )

    _write_profile(
        tmp_path,
        "adapter_live",
        "version: 1\nintegration_adapter_writer:\n  enabled: true\n  stub_only: false\n",
    )
    payload = integration_adapter_writer_workflow_explainer_payload(tmp_path, "adapter_live")
    assert payload["would_emit_stage_started"] is True
    assert payload["scaffold_status"] == "live_adapter_recorded"
    m = integration_adapter_writer_workflow_explainer_operator_metrics(payload)
    assert m["would_emit_stage_started"] is True
    assert m["live_path_active"] is True
    cap = integration_adapter_writer_workflow_explainer_operator_metrics_caption(m)
    assert cap is not None
    assert "live path" in cap
    assert "live ``stage.started``" in cap


def test_emit_stub_integration_adapter_writer_stage_direct() -> None:
    from hermes_store.memory import InMemoryEventStore

    store = InMemoryEventStore()
    from uuid import uuid4

    rid = uuid4()
    block = IntegrationAdapterWriterWorkflowBlock(
        enabled=True,
        target_adapter_kind="api_bridge",
        stub_only=True,
    )
    emit_stub_integration_adapter_writer_stage(store, run_id=rid, block=block)
    evs = store.list_run_events(str(rid))
    row = next(
        r
        for r in evs
        if (r.get("payload") or {}).get("stage_name") == INTEGRATION_ADAPTER_WRITER_STAGE
    )
    meta = row.get("metadata") or {}
    iaw = meta.get("integration_adapter_writer") or {}
    assert iaw.get("scaffold_status") == "stub_only"
