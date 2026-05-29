"""Workflow YAML knobs for ``refactor`` stage."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hermes_orchestrator.workflow_profiles import workflow_profile_dict


@dataclass(frozen=True)
class RefactorWorkflowBlock:
    enabled: bool = False
    stub_only: bool = True
    max_iterations: int = 1
    llm_enabled: bool = False


def parse_refactor_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> RefactorWorkflowBlock:
    if workflow_profile is None or not str(workflow_profile).strip():
        return RefactorWorkflowBlock()
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return RefactorWorkflowBlock()
    block = raw.get("refactor")
    if not isinstance(block, dict):
        return RefactorWorkflowBlock()
    try:
        max_iter = int(block.get("max_iterations", 1) or 1)
    except (TypeError, ValueError):
        max_iter = 1
    return RefactorWorkflowBlock(
        enabled=bool(block.get("enabled", False)),
        stub_only=bool(block.get("stub_only", True)),
        max_iterations=max(1, min(5, max_iter)),
        llm_enabled=bool(block.get("llm_enabled", False)),
    )


def refactor_stage_effective(block: RefactorWorkflowBlock) -> bool:
    env_raw = os.environ.get("HERMES_REFACTOR_STAGE", "").strip().lower()
    if env_raw in ("0", "false", "no"):
        return False
    if env_raw in ("1", "true", "yes"):
        return True
    return block.enabled
