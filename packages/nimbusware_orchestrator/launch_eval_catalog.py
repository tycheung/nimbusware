"""Load launch eval prompt catalog from configs/launch_eval/catalog.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nimbusware_env import find_repo_root


def catalog_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "launch_eval" / "catalog.yaml"


def load_launch_eval_catalog(repo_root: Path | None = None) -> dict[str, Any]:
    path = catalog_path(repo_root)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def default_workspace_paths(repo_root: Path | None = None) -> tuple[Path, ...]:
    root = repo_root or find_repo_root()
    doc = load_launch_eval_catalog(root)
    paths: list[Path] = []
    for entry in doc.get("default_workspaces") or []:
        rel = Path(str(entry))
        candidate = rel if rel.is_absolute() else (root / rel)
        paths.append(candidate.resolve())
    return tuple(paths)


def prompt_ids(repo_root: Path | None = None) -> tuple[str, ...]:
    doc = load_launch_eval_catalog(repo_root)
    return tuple(str(p["id"]) for p in doc.get("prompts") or [] if p.get("id"))
