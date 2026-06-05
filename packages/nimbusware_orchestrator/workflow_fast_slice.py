"""Parse workflow ``fast_slice`` opt-in for skipping low-severity critic matrix."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict


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
