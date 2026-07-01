from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_console.explainer_core.env_summaries import env_tri_state_summary
from nimbusware_console.explainer_core.repo_yaml import json_safe_yaml_fragment
from nimbusware_console.explainer_core.workflow_payload_header import workflow_payload_header
from nimbusware_orchestrator.integration_adapter_writer_stage import (
    integration_adapter_writer_stage_would_emit,
)
from nimbusware_orchestrator.workflow_blocks_simple import (
    integration_adapter_writer_effective,
    parse_integration_adapter_writer_workflow_block,
)


def _nimbusware_integration_adapter_writer_env_summary() -> dict[str, Any]:
    return env_tri_state_summary("NIMBUSWARE_INTEGRATION_ADAPTER_WRITER")


def integration_adapter_writer_fleet_manifest_count(repo_root: Path) -> int:
    manifest_dir = repo_root / ".nimbusware" / "integration_adapter_writer"
    if not manifest_dir.is_dir():
        return 0
    return sum(1 for path in manifest_dir.rglob("manifest.json") if path.is_file())


def integration_adapter_writer_workflow_explainer_payload(
    repo_root: Path,
    workflow_profile: str | None,
) -> dict[str, Any]:
    snap, header = workflow_payload_header(repo_root, workflow_profile)
    wf_sel = snap.workflow_profile
    materializer = snap.materializer
    block = parse_integration_adapter_writer_workflow_block(
        repo_root,
        wf_sel,
        config_materializer=materializer,
    )
    effective = integration_adapter_writer_effective(block)
    would_emit = integration_adapter_writer_stage_would_emit(
        repo_root,
        wf_sel,
        config_materializer=materializer,
    )
    out: dict[str, Any] = {
        **header,
        "NIMBUSWARE_INTEGRATION_ADAPTER_WRITER": _nimbusware_integration_adapter_writer_env_summary(),
        "workflow_block": {
            "enabled": block.enabled,
            "target_adapter_kind": block.target_adapter_kind,
            "stub_only": block.stub_only,
        },
        "effective_enabled": effective,
        "would_emit_stage_started": would_emit,
        "scaffold_status": ("stub_only" if block.stub_only else "live_adapter_recorded"),
        "fleet_workspace_manifest_count": integration_adapter_writer_fleet_manifest_count(
            repo_root,
        ),
    }
    relpath = header.get("workflow_yaml_relpath")
    if isinstance(relpath, str) and relpath.strip():
        out["workflow_yaml_path"] = relpath
    sub = snap.disk_doc.get("integration_adapter_writer")
    if sub is not None:
        out["workflow_yaml_fragment"] = json_safe_yaml_fragment(sub)
    return out
