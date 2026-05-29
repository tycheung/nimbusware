"""Workflow YAML knobs for self-refinement stage marker (plan §14 #17)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hermes_orchestrator.workflow_profiles import workflow_profile_dict


@dataclass(frozen=True)
class SelfRefinementWorkflowBlock:
    """Parsed ``self_refinement`` subsection from ``configs/workflows/{profile}.yaml``."""

    enabled: bool = False
    version: int | None = None
    description: str | None = None
    max_iterations: int | None = None
    auto_promote_probation: bool = False
    llm_critique_enabled: bool = False
    ungated_loop: bool = False


def parse_self_refinement_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> SelfRefinementWorkflowBlock:
    """Return workflow self_refinement overrides; missing block → ``enabled=False``."""
    if workflow_profile is None or not str(workflow_profile).strip():
        return SelfRefinementWorkflowBlock()
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return SelfRefinementWorkflowBlock()
    block = raw.get("self_refinement")
    if not isinstance(block, dict):
        return SelfRefinementWorkflowBlock()
    enabled = bool(block.get("enabled", False))
    ver_raw = block.get("version")
    version: int | None = None
    if ver_raw is not None:
        try:
            version = int(ver_raw)
        except (TypeError, ValueError):
            version = None
    desc_raw = block.get("description")
    description: str | None = None
    if isinstance(desc_raw, str) and desc_raw.strip():
        description = desc_raw.strip()
    max_iter: int | None = None
    mi_raw = block.get("max_iterations")
    if mi_raw is not None:
        try:
            parsed = int(mi_raw)
            if parsed >= 1:
                max_iter = parsed
        except (TypeError, ValueError):
            max_iter = None
    auto_promote = bool(block.get("auto_promote_probation", False))
    llm_critique = bool(block.get("llm_critique_enabled", False))
    ungated_loop = bool(block.get("ungated_loop", False))
    return SelfRefinementWorkflowBlock(
        enabled=enabled,
        version=version,
        description=description,
        max_iterations=max_iter,
        auto_promote_probation=auto_promote,
        llm_critique_enabled=llm_critique,
        ungated_loop=ungated_loop,
    )


def self_refinement_ungated_loop_effective(block: SelfRefinementWorkflowBlock) -> bool:
    """YAML ``ungated_loop`` unless ``HERMES_SELF_REFINEMENT_UNGATED_LOOP`` overrides."""
    import os

    env_raw = os.environ.get("HERMES_SELF_REFINEMENT_UNGATED_LOOP", "").strip().lower()
    if env_raw in ("1", "true", "yes"):
        return True
    if env_raw in ("0", "false", "no"):
        return False
    return block.ungated_loop


def self_refinement_production_ungated_effective(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> bool:
    """Ungated iterative depth from YAML without env kill-switches."""
    import os

    block = parse_self_refinement_workflow_block(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    if not block.enabled or not block.ungated_loop:
        return False
    if os.environ.get("HERMES_SELF_REFINEMENT_STAGE_MARKER", "").strip().lower() in (
        "0",
        "false",
        "no",
    ):
        return False
    if os.environ.get("HERMES_SELF_REFINEMENT_UNGATED_LOOP", "").strip().lower() in (
        "0",
        "false",
        "no",
    ):
        return False
    return True


def self_refinement_llm_critique_branch_effective(block: SelfRefinementWorkflowBlock) -> bool:
    """YAML ``llm_critique_enabled`` unless ``HERMES_USE_LLM`` is explicitly off."""
    import os

    if not block.llm_critique_enabled:
        return False
    env_raw = os.environ.get("HERMES_USE_LLM", "").strip().lower()
    if env_raw in ("0", "false", "no"):
        return False
    return True


def self_refinement_production_llm_critique_effective(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> bool:
    """Live Ollama SR critique on production profiles without requiring ``HERMES_USE_LLM=1``."""
    import os

    profile = (workflow_profile or "").strip()
    if profile not in ("nimbusware_production", "self_refinement_production_ungated"):
        return False
    block = parse_self_refinement_workflow_block(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    if not block.enabled or not block.llm_critique_enabled:
        return False
    if os.environ.get("HERMES_SELF_REFINEMENT_STAGE_MARKER", "").strip().lower() in (
        "0",
        "false",
        "no",
    ):
        return False
    if os.environ.get("HERMES_USE_LLM", "").strip().lower() in ("0", "false", "no"):
        return False
    return True


def self_refinement_llm_critique_effective_for_run(
    repo_root: Path,
    workflow_profile: str | None,
    block: SelfRefinementWorkflowBlock,
    *,
    config_materializer: Any | None = None,
) -> bool:
    """Union of YAML branch + production profile live Ollama path (§14 #17 optional)."""
    if self_refinement_llm_critique_branch_effective(block):
        return True
    return self_refinement_production_llm_critique_effective(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
