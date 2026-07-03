from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from env.env_flags import env_force_off, env_force_on
from orchestrator.workflow_profiles import (
    coerce_yaml_bool,
    load_profile_subsection,
    workflow_profile_dict,
)

DEFAULT_ADAPTER_KIND = "compatibility_shim"


@dataclass(frozen=True)
class EscalationWorkflowBlock:
    suppress_automatic_escalation: bool = False


def _escalation_from_block(block: dict[str, Any]) -> EscalationWorkflowBlock:
    return EscalationWorkflowBlock(
        suppress_automatic_escalation=coerce_yaml_bool(
            block.get("suppress_automatic_escalation", False),
        ),
    )


def parse_escalation_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> EscalationWorkflowBlock:
    return load_profile_subsection(
        repo_root,
        workflow_profile,
        "escalation",
        _escalation_from_block,
        default=EscalationWorkflowBlock(),
        config_materializer=config_materializer,
    )


@dataclass(frozen=True)
class TheaterWorkflowBlock:
    enabled: bool = True
    max_message_chars: int = 1200
    show_evidence_links: bool = True
    llm_summary: bool = False


def _theater_from_block(block: dict[str, Any]) -> TheaterWorkflowBlock:
    return TheaterWorkflowBlock(
        enabled=bool(block.get("enabled", True)),
        max_message_chars=max(200, int(block.get("max_message_chars", 1200) or 1200)),
        show_evidence_links=bool(block.get("show_evidence_links", True)),
        llm_summary=bool(block.get("llm_summary", False)),
    )


def parse_theater_workflow_block(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> TheaterWorkflowBlock:
    return load_profile_subsection(
        repo_root,
        workflow_profile,
        "theater",
        _theater_from_block,
        default=TheaterWorkflowBlock(),
        config_materializer=config_materializer,
    )


def theater_effective_metadata(block: TheaterWorkflowBlock) -> dict[str, Any]:
    return {
        "enabled": block.enabled,
        "max_message_chars": block.max_message_chars,
        "show_evidence_links": block.show_evidence_links,
        "llm_summary": block.llm_summary,
    }


@dataclass(frozen=True)
class DevEnvWorkflowBlock:
    enabled: bool = False
    human_fidelity_enabled: bool = False
    ui_controller_enabled: bool = False
    ui_controller_required: bool = False


def _dev_env_from_block(block: dict[str, Any]) -> DevEnvWorkflowBlock:
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


def parse_dev_env_workflow_block(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> DevEnvWorkflowBlock:
    return load_profile_subsection(
        repo_root,
        workflow_profile,
        "dev_env",
        _dev_env_from_block,
        default=DevEnvWorkflowBlock(),
        config_materializer=config_materializer,
    )


def dev_env_effective_metadata(block: DevEnvWorkflowBlock) -> dict[str, Any]:
    return {
        "enabled": block.enabled,
        "human_fidelity_enabled": block.human_fidelity_enabled,
        "ui_controller_enabled": block.ui_controller_enabled,
        "ui_controller_required": block.ui_controller_required,
    }


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
    if env_force_off("NIMBUSWARE_INTEGRATION_ADAPTER_WRITER"):
        return False
    if env_force_on("NIMBUSWARE_INTEGRATION_ADAPTER_WRITER"):
        return True
    return block.enabled


@dataclass(frozen=True)
class FastSliceWorkflowBlock:
    enabled: bool = False


def parse_fast_slice_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> FastSliceWorkflowBlock:
    if workflow_profile is None or not str(workflow_profile).strip():
        return FastSliceWorkflowBlock()
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return FastSliceWorkflowBlock()
    if bool(raw.get("fast_slice", False)):
        return FastSliceWorkflowBlock(enabled=True)
    slice_raw = raw.get("slice")
    if isinstance(slice_raw, dict) and bool(slice_raw.get("fast_slice", False)):
        return FastSliceWorkflowBlock(enabled=True)
    return FastSliceWorkflowBlock()


def fast_slice_effective_metadata(block: FastSliceWorkflowBlock) -> dict[str, Any]:
    return {"enabled": block.enabled}


@dataclass(frozen=True)
class MicroSliceWorkflowBlock:
    enabled: bool = False
    max_files: int = 3
    max_loc: int = 120
    allowed_globs: tuple[str, ...] = ("**/*.py",)
    e2e_enabled: bool = False
    e2e_command: str | None = None


def parse_micro_slice_workflow_block(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> MicroSliceWorkflowBlock:
    wf = workflow_profile_dict(repo_root, workflow_profile, materializer=config_materializer)
    raw = wf.get("slice")
    if not isinstance(raw, dict):
        return MicroSliceWorkflowBlock()
    enabled = bool(raw.get("enabled", False))
    max_files = int(raw.get("max_files", 3) or 3)
    max_loc = int(raw.get("max_loc", 120) or 120)
    globs_raw = raw.get("allowed_globs")
    if isinstance(globs_raw, list):
        globs = tuple(str(g) for g in globs_raw if str(g).strip())
    else:
        globs = ("**/*.py",)
    e2e_raw = raw.get("e2e")
    e2e_enabled = False
    e2e_command: str | None = None
    if isinstance(e2e_raw, dict):
        e2e_enabled = bool(e2e_raw.get("enabled", False))
        cmd = e2e_raw.get("command")
        if isinstance(cmd, str) and cmd.strip():
            e2e_command = cmd.strip()
    return MicroSliceWorkflowBlock(
        enabled=enabled,
        max_files=max(1, max_files),
        max_loc=max(1, max_loc),
        allowed_globs=globs or ("**/*.py",),
        e2e_enabled=e2e_enabled,
        e2e_command=e2e_command,
    )
