from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict


@dataclass(frozen=True)
class DevEnvWorkflowBlock:
    enabled: bool = False
    human_fidelity_enabled: bool = False
    ui_controller_enabled: bool = False
    ui_controller_required: bool = False


def parse_dev_env_workflow_block(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> DevEnvWorkflowBlock:
    try:
        raw = workflow_profile_dict(repo_root, workflow_profile, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return DevEnvWorkflowBlock()
    block = raw.get("dev_env")
    if not isinstance(block, dict):
        return DevEnvWorkflowBlock()
    ui = block.get("ui_controller")
    ui_enabled = False
    ui_required = False
    if isinstance(ui, dict):
        ui_enabled = bool(ui.get("enabled", False))
        ui_required = bool(ui.get("required", False))
    hf = block.get("human_fidelity")
    hf_enabled = bool(hf.get("enabled", False)) if isinstance(hf, dict) else False
    return DevEnvWorkflowBlock(
        enabled=bool(block.get("enabled", False)),
        human_fidelity_enabled=hf_enabled,
        ui_controller_enabled=ui_enabled,
        ui_controller_required=ui_required,
    )


def dev_env_effective_metadata(block: DevEnvWorkflowBlock) -> dict[str, Any]:
    return {
        "enabled": block.enabled,
        "human_fidelity_enabled": block.human_fidelity_enabled,
        "ui_controller_enabled": block.ui_controller_enabled,
        "ui_controller_required": block.ui_controller_required,
    }
