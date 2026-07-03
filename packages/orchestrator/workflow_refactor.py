from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from env.env_flags import env_force_off, env_force_on
from orchestrator.workflow_profiles import load_profile_subsection


@dataclass(frozen=True)
class RefactorWorkflowBlock:
    enabled: bool = False
    stub_only: bool = False
    max_iterations: int = 1
    llm_enabled: bool = False
    orphan_gate_max: int | None = None


def _refactor_from_block(block: dict[str, Any]) -> RefactorWorkflowBlock:
    try:
        max_iter = int(block.get("max_iterations", 1) or 1)
    except (TypeError, ValueError):
        max_iter = 1
    raw_og = block.get("orphan_gate_max")
    orphan_gate_max: int | None = None
    if isinstance(raw_og, int) and not isinstance(raw_og, bool) and raw_og >= 0:
        orphan_gate_max = raw_og
    return RefactorWorkflowBlock(
        enabled=bool(block.get("enabled", False)),
        stub_only=bool(block.get("stub_only", False)),
        max_iterations=max(1, min(5, max_iter)),
        llm_enabled=bool(block.get("llm_enabled", False)),
        orphan_gate_max=orphan_gate_max,
    )


def parse_refactor_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> RefactorWorkflowBlock:
    return load_profile_subsection(
        repo_root,
        workflow_profile,
        "refactor",
        _refactor_from_block,
        default=RefactorWorkflowBlock(),
        config_materializer=config_materializer,
    )


def refactor_stage_effective(block: RefactorWorkflowBlock) -> bool:
    if env_force_off("NIMBUSWARE_REFACTOR_STAGE"):
        return False
    if env_force_on("NIMBUSWARE_REFACTOR_STAGE"):
        return True
    return block.enabled


__all__ = (
    "RefactorWorkflowBlock",
    "parse_refactor_workflow_block",
    "refactor_stage_effective",
)
