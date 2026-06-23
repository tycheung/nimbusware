from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_console.components.workflow_explainer_helpers import (
    json_safe_yaml_fragment,
    relative_under,
)
from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_core.env_summaries import env_tri_state_summary
from nimbusware_orchestrator.integration_adapter_writer_stage import (
    integration_adapter_writer_stage_would_emit,
)
from nimbusware_orchestrator.workflow_integration_adapter_writer import (
    integration_adapter_writer_effective,
    parse_integration_adapter_writer_workflow_block,
)
from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict, workflow_profile_path


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
    materializer = console_config_materializer(repo_root)
    block = parse_integration_adapter_writer_workflow_block(
        repo_root,
        workflow_profile,
        config_materializer=materializer,
    )
    effective = integration_adapter_writer_effective(block)
    would_emit = integration_adapter_writer_stage_would_emit(
        repo_root,
        workflow_profile,
        config_materializer=materializer,
    )
    out: dict[str, Any] = {
        "workflow_profile": workflow_profile,
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
    if workflow_profile:
        try:
            path = workflow_profile_path(repo_root, str(workflow_profile).strip())
            out["workflow_yaml_path"] = relative_under(repo_root, path)
            raw = workflow_profile_dict(
                repo_root,
                str(workflow_profile).strip(),
                materializer=materializer,
            )
            sub = raw.get("integration_adapter_writer")
            if sub is not None:
                out["workflow_yaml_fragment"] = json_safe_yaml_fragment(sub)
        except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError) as exc:
            out["load_error"] = str(exc)
    return out
