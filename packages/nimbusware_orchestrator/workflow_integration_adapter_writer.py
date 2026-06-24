from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_profiles import load_profile_subsection

DEFAULT_ADAPTER_KIND = "compatibility_shim"


@dataclass(frozen=True)
class IntegrationAdapterWriterWorkflowBlock:
    enabled: bool = False
    target_adapter_kind: str = DEFAULT_ADAPTER_KIND
    stub_only: bool = False


def _iaw_from_block(block: dict[str, Any]) -> IntegrationAdapterWriterWorkflowBlock:
    enabled = bool(block.get("enabled", False))
    kind_raw = block.get("target_adapter_kind", DEFAULT_ADAPTER_KIND)
    kind = str(kind_raw).strip() if kind_raw is not None else DEFAULT_ADAPTER_KIND
    if not kind:
        kind = DEFAULT_ADAPTER_KIND
    return IntegrationAdapterWriterWorkflowBlock(
        enabled=enabled,
        target_adapter_kind=kind,
        stub_only=bool(block.get("stub_only", True)),
    )


def parse_integration_adapter_writer_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> IntegrationAdapterWriterWorkflowBlock:
    return load_profile_subsection(
        repo_root,
        workflow_profile,
        "integration_adapter_writer",
        _iaw_from_block,
        default=IntegrationAdapterWriterWorkflowBlock(),
        config_materializer=config_materializer,
    )


def integration_adapter_writer_effective(
    block: IntegrationAdapterWriterWorkflowBlock,
) -> bool:
    from nimbusware_env.env_flags import env_force_off, env_force_on

    if env_force_off("NIMBUSWARE_INTEGRATION_ADAPTER_WRITER"):
        return False
    if env_force_on("NIMBUSWARE_INTEGRATION_ADAPTER_WRITER"):
        return True
    return block.enabled
