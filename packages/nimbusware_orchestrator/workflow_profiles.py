"""Resolve ``workflow_profile`` string to YAML path under ``configs/workflows/``."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, cast

from nimbusware_orchestrator.merge import load_yaml


def workflow_profile_path(repo_root: Path, profile: str) -> Path:
    """Return path to ``{repo_root}/configs/workflows/{profile}.yaml`` if it exists."""
    key = profile.strip()
    if not key or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", key):
        msg = f"invalid workflow_profile: {profile!r}"
        raise ValueError(msg)
    path = repo_root / "configs" / "workflows" / f"{key}.yaml"
    if not path.is_file():
        msg = f"unknown workflow_profile (no file): {profile!r}"
        raise FileNotFoundError(msg)
    return path


def workflow_profile_dict(
    repo_root: Path,
    profile: str,
    *,
    materializer: Any | None = None,
) -> dict[str, Any]:
    """Load workflow profile from materializer (DB mode) or on-disk YAML."""
    if materializer is not None and getattr(materializer, "use_db", False):
        return cast(dict[str, Any], materializer.get_workflow_profile_dict(profile))
    return load_yaml(workflow_profile_path(repo_root, profile))
