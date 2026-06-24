from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, cast

from nimbusware_orchestrator.merge import load_yaml

T = TypeVar("T")
ProfileLoadErrors = (
    FileNotFoundError,
    KeyError,
    OSError,
    ValueError,
    UnicodeDecodeError,
)


def workflow_profile_path(repo_root: Path, profile: str) -> Path:
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
    if materializer is not None and getattr(materializer, "use_db", False):
        return cast(dict[str, Any], materializer.get_workflow_profile_dict(profile))
    return load_yaml(workflow_profile_path(repo_root, profile))


def load_workflow_profile_dict(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any] | None:
    if workflow_profile is None or not str(workflow_profile).strip():
        return None
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except ProfileLoadErrors:
        return None
    return raw if isinstance(raw, dict) else None


def load_profile_subsection(
    repo_root: Path,
    workflow_profile: str | None,
    yaml_key: str,
    factory: Callable[[dict[str, Any]], T],
    *,
    default: T,
    config_materializer: Any | None = None,
) -> T:
    raw = load_workflow_profile_dict(
        repo_root, workflow_profile, config_materializer=config_materializer
    )
    if raw is None:
        return default
    block = raw.get(yaml_key)
    if not isinstance(block, dict):
        return default
    return factory(block)


def coerce_yaml_bool(raw: Any, *, default: bool = False) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return default
