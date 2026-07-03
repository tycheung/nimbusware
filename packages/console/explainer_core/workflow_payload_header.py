from __future__ import annotations

from pathlib import Path
from typing import Any

from console.explainer_core.workflow_profile import (
    WorkflowDiskSnapshot,
    load_workflow_disk_snapshot,
)


def workflow_payload_header(
    repo_root: Path,
    workflow_profile: str | None,
) -> tuple[WorkflowDiskSnapshot, dict[str, Any]]:
    snap = load_workflow_disk_snapshot(repo_root, workflow_profile)
    header: dict[str, Any] = {
        "workflow_profile": snap.workflow_profile,
        "workflow_yaml_relpath": snap.workflow_yaml_relpath,
        "load_error": snap.load_error,
        "workflow_yaml_top_level_version_int": snap.version_int,
        "workflow_yaml_file_bytes": snap.file_bytes,
    }
    return snap, header
