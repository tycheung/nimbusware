"""Workflow YAML knobs for ``performance_critique`` (Phase 3 / fo144)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hermes_orchestrator.workflow_profiles import workflow_profile_dict


@dataclass(frozen=True)
class PerformanceCritiqueBlock:
    enabled: bool = False
    stub: bool = True
    llm_enabled: bool = False
    severity_floor: str = "MEDIUM"


def parse_performance_critique_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> PerformanceCritiqueBlock:
    if workflow_profile is None or not str(workflow_profile).strip():
        return PerformanceCritiqueBlock()
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return PerformanceCritiqueBlock()
    block = raw.get("performance_critique")
    if not isinstance(block, dict):
        return PerformanceCritiqueBlock()
    floor_raw = block.get("severity_floor", "MEDIUM")
    return PerformanceCritiqueBlock(
        enabled=bool(block.get("enabled", False)),
        stub=bool(block.get("stub", True)),
        llm_enabled=bool(block.get("llm_enabled", False)),
        severity_floor=str(floor_raw).strip().upper() or "MEDIUM",
    )


def performance_critique_effective(block: PerformanceCritiqueBlock) -> bool:
    env_raw = os.environ.get("HERMES_PERFORMANCE_CRITIQUE", "").strip().lower()
    if env_raw in ("0", "false", "no"):
        return False
    if env_raw in ("1", "true", "yes"):
        return True
    return block.enabled


def performance_critique_llm_branch_effective(block: PerformanceCritiqueBlock) -> bool:
    env_raw = os.environ.get("HERMES_PERFORMANCE_CRITIQUE_LLM", "").strip().lower()
    if env_raw in ("0", "false", "no"):
        return False
    if env_raw in ("1", "true", "yes"):
        return True
    if os.environ.get("HERMES_USE_LLM", "").strip().lower() in ("0", "false", "no"):
        return False
    return block.llm_enabled
