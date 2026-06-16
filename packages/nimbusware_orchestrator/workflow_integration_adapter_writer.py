from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict

DEFAULT_ADAPTER_KIND = "compatibility_shim"


@dataclass(frozen=True)
class IntegrationAdapterWriterWorkflowBlock:
    enabled: bool = False
    target_adapter_kind: str = DEFAULT_ADAPTER_KIND
    stub_only: bool = True


def parse_integration_adapter_writer_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> IntegrationAdapterWriterWorkflowBlock:
    if workflow_profile is None or not str(workflow_profile).strip():
        return IntegrationAdapterWriterWorkflowBlock()
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return IntegrationAdapterWriterWorkflowBlock()
    block = raw.get("integration_adapter_writer")
    if not isinstance(block, dict):
        return IntegrationAdapterWriterWorkflowBlock()
    enabled = bool(block.get("enabled", False))
    kind_raw = block.get("target_adapter_kind", DEFAULT_ADAPTER_KIND)
    kind = str(kind_raw).strip() if kind_raw is not None else DEFAULT_ADAPTER_KIND
    if not kind:
        kind = DEFAULT_ADAPTER_KIND
    stub_only = bool(block.get("stub_only", True))
    return IntegrationAdapterWriterWorkflowBlock(
        enabled=enabled,
        target_adapter_kind=kind,
        stub_only=stub_only,
    )


def integration_adapter_writer_effective(
    block: IntegrationAdapterWriterWorkflowBlock,
) -> bool:
    """Env ``NIMBUSWARE_INTEGRATION_ADAPTER_WRITER=0`` kill-switch overrides workflow YAML."""
    from nimbusware_env.env_flags import env_force_off, env_force_on

    if env_force_off("NIMBUSWARE_INTEGRATION_ADAPTER_WRITER"):
        return False
    if env_force_on("NIMBUSWARE_INTEGRATION_ADAPTER_WRITER"):
        return True
    return block.enabled
