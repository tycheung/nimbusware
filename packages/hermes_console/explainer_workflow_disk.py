"""On-disk workflow YAML for console explainers when a profile file exists."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_orchestrator.merge import load_yaml
from hermes_orchestrator.workflow_profiles import workflow_profile_path


def workflow_profile_expected_path(repo_root: Path, profile: str) -> Path:
    """Path where a workflow profile file would live (may be absent in DB-only mode)."""
    key = profile.strip()
    return repo_root / "configs" / "workflows" / f"{key}.yaml"


def workflow_profile_disk_snapshot(
    repo_root: Path,
    profile: str,
) -> tuple[dict[str, Any], Path, int | None]:
    """Load ``configs/workflows/{profile}.yaml`` from disk."""
    wp = workflow_profile_path(repo_root, profile)
    file_bytes: int | None = None
    try:
        file_bytes = int(wp.stat().st_size)
    except OSError:
        file_bytes = None
    return load_yaml(wp), wp, file_bytes


def load_workflow_profile_documents(
    repo_root: Path,
    profile: str,
    *,
    materializer: Any | None,
) -> tuple[dict[str, Any], dict[str, Any], Path, int | None]:
    """Return ``(disk_doc, effective_doc, path, file_bytes)`` for explainer payloads.

    YAML presence metrics use ``disk_doc`` (on-disk when present). Effective paths use
    ``effective_doc`` (materializer when DB mode is on, else disk). When Postgres
    config mode is active and the workflow file is absent on disk, ``disk_doc`` mirrors
    the materialized document so explainers do not surface a false load error.
    """
    wp = workflow_profile_expected_path(repo_root, profile)
    use_db = materializer is not None and getattr(materializer, "use_db", False)

    if use_db:
        effective_doc = materializer.get_workflow_profile_dict(profile)
        if wp.is_file():
            disk_doc, _, file_bytes = workflow_profile_disk_snapshot(repo_root, profile)
        else:
            disk_doc = effective_doc
            file_bytes = None
        return disk_doc, effective_doc, wp, file_bytes

    disk_doc, wp, file_bytes = workflow_profile_disk_snapshot(repo_root, profile)
    return disk_doc, disk_doc, wp, file_bytes
