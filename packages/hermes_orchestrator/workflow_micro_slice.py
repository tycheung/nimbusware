"""Parse workflow ``slice`` block for micro-slice orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hermes_orchestrator.workflow_profiles import workflow_profile_dict


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
