from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, cast

from orchestrator.merge import load_yaml

T = TypeVar("T")
ProfileLoadErrors = (
    FileNotFoundError,
    KeyError,
    OSError,
    ValueError,
    UnicodeDecodeError,
)

_FRAGMENT_PREFIX = "fragments/"
_PROFILE_NAME_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*")
_FRAGMENT_NAME_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*")


def _is_fragment_key(key: str) -> bool:
    return key.startswith(_FRAGMENT_PREFIX)


def workflow_yaml_path_for_key(repo_root: Path, key: str) -> Path:
    """Resolve a workflow profile or ``fragments/<name>`` fragment to its YAML path."""
    k = key.strip()
    if _is_fragment_key(k):
        name = k[len(_FRAGMENT_PREFIX) :]
        if not name or not _FRAGMENT_NAME_RE.fullmatch(name):
            msg = f"invalid workflow fragment: {key!r}"
            raise ValueError(msg)
        path = repo_root / "configs" / "workflows" / "fragments" / f"{name}.yaml"
        if not path.is_file():
            msg = f"unknown workflow fragment (no file): {key!r}"
            raise FileNotFoundError(msg)
        return path
    if not k or not _PROFILE_NAME_RE.fullmatch(k):
        msg = f"invalid workflow_profile: {key!r}"
        raise ValueError(msg)
    path = repo_root / "configs" / "workflows" / f"{k}.yaml"
    if not path.is_file():
        msg = f"unknown workflow_profile (no file): {key!r}"
        raise FileNotFoundError(msg)
    return path


def _deep_merge_workflow(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if key == "extends":
            continue
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_workflow(existing, value)
        else:
            merged[key] = value
    return merged


def _load_workflow_yaml_raw(
    repo_root: Path,
    key: str,
    *,
    materializer: Any | None = None,
) -> dict[str, Any]:
    if _is_fragment_key(key):
        return load_yaml(workflow_yaml_path_for_key(repo_root, key))
    if materializer is not None and getattr(materializer, "use_db", False):
        return cast(dict[str, Any], materializer.get_workflow_profile_dict(key))
    return load_yaml(workflow_profile_path(repo_root, key))


def collect_workflow_extends_trace(
    repo_root: Path,
    profile: str,
    *,
    materializer: Any | None = None,
    _stack: tuple[str, ...] = (),
) -> list[str]:
    key = profile.strip()
    if key in _stack:
        chain = " -> ".join((*_stack, key))
        msg = f"workflow_profile extends cycle: {chain}"
        raise ValueError(msg)
    if _is_fragment_key(key):
        path = workflow_yaml_path_for_key(repo_root, key)
        trace = [f"extends:fragment {key} <- {path.relative_to(repo_root.resolve())}"]
    elif materializer is not None and getattr(materializer, "use_db", False):
        trace = [f"extends:db workflows/{key}"]
    else:
        path = workflow_profile_path(repo_root, key)
        trace = [f"extends:yaml {key} <- {path.relative_to(repo_root.resolve())}"]
    raw = _load_workflow_yaml_raw(repo_root, key, materializer=materializer)
    extends = raw.get("extends")
    if extends is None:
        return trace
    parent_key = str(extends).strip()
    if not parent_key:
        return trace
    return [*collect_workflow_extends_trace(
        repo_root,
        parent_key,
        materializer=materializer,
        _stack=(*_stack, key),
    ), *trace]


def _resolve_workflow_profile_raw(
    repo_root: Path,
    profile: str,
    *,
    materializer: Any | None = None,
    _stack: tuple[str, ...] = (),
) -> dict[str, Any]:
    key = profile.strip()
    if key in _stack:
        chain = " -> ".join((*_stack, key))
        msg = f"workflow_profile extends cycle: {chain}"
        raise ValueError(msg)
    raw = _load_workflow_yaml_raw(repo_root, key, materializer=materializer)
    extends = raw.get("extends")
    if extends is None:
        return dict(raw)
    parent_key = str(extends).strip()
    if not parent_key:
        return dict(raw)
    parent = _resolve_workflow_profile_raw(
        repo_root,
        parent_key,
        materializer=materializer,
        _stack=(*_stack, key),
    )
    overlay = {k: v for k, v in raw.items() if k != "extends"}
    return _deep_merge_workflow(parent, overlay)


def workflow_profile_path(repo_root: Path, profile: str) -> Path:
    key = profile.strip()
    if _is_fragment_key(key):
        msg = f"invalid workflow_profile: {profile!r}"
        raise ValueError(msg)
    if not key or not _PROFILE_NAME_RE.fullmatch(key):
        msg = f"invalid workflow_profile: {profile!r}"
        raise ValueError(msg)
    path = repo_root / "configs" / "workflows" / f"{key}.yaml"
    if not path.is_file():
        msg = f"unknown workflow_profile (no file): {profile!r}"
        raise FileNotFoundError(msg)
    return path


def list_workflow_profile_names(repo_root: Path) -> tuple[str, ...]:
    workflows_dir = repo_root / "configs" / "workflows"
    if not workflows_dir.is_dir():
        return ()
    names: list[str] = []
    for path in sorted(workflows_dir.glob("*.yaml")):
        stem = path.stem
        if stem.startswith("_"):
            continue
        names.append(stem)
    return tuple(names)


def workflow_profile_dict(
    repo_root: Path,
    profile: str,
    *,
    materializer: Any | None = None,
) -> dict[str, Any]:
    if materializer is not None and getattr(materializer, "use_db", False):
        return cast(dict[str, Any], materializer.get_workflow_profile_dict(profile))
    return _resolve_workflow_profile_raw(repo_root, profile, materializer=materializer)


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
