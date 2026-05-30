"""Resolve workspace path for a run from project metadata."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import UUID

from agent_core.models import EventType


def project_from_run_created_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(metadata, dict):
        return None
    project = metadata.get("project")
    return dict(project) if isinstance(project, dict) else None


def project_id_from_run_created_metadata(metadata: dict[str, Any] | None) -> str | None:
    project = project_from_run_created_metadata(metadata)
    if project is None:
        return None
    pid = project.get("id") or project.get("project_id")
    return str(pid).strip() if pid else None


def workspace_path_from_run_created_metadata(metadata: dict[str, Any] | None) -> Path | None:
    project = project_from_run_created_metadata(metadata)
    if project is None:
        return None
    raw = project.get("workspace_path")
    if not raw:
        return None
    return Path(str(raw)).resolve()


def run_created_metadata_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if row.get("event_type") == EventType.RUN_CREATED.value:
            meta = row.get("metadata")
            return dict(meta) if isinstance(meta, dict) else {}
    return {}


def resolve_run_workspace(
    rows: list[dict[str, Any]],
    *,
    override: Path | None = None,
) -> Path:
    """Pick workspace for slice execution: explicit override → env → project metadata → cwd."""
    if override is not None:
        return override.resolve()
    env_ws = os.environ.get("HERMES_WORKSPACE", "").strip()
    if env_ws:
        return Path(env_ws).resolve()
    meta = run_created_metadata_from_rows(rows)
    project_ws = workspace_path_from_run_created_metadata(meta)
    if project_ws is not None:
        return project_ws
    return Path(".").resolve()


def project_metadata_block(
    *,
    project_id: UUID,
    name: str,
    workspace_path: Path,
    template: str,
) -> dict[str, str]:
    return {
        "id": str(project_id),
        "name": name,
        "workspace_path": str(workspace_path.resolve()),
        "template": template,
    }
