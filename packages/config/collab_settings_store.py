from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from env import find_repo_root


def collab_settings_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / ".nimbusware" / "platform" / "collab_settings.yaml"


def load_collab_settings(repo_root: Path | None = None) -> dict[str, Any]:
    path = collab_settings_path(repo_root)
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def load_persisted_collab_enabled(repo_root: Path | None = None) -> bool | None:
    doc = load_collab_settings(repo_root)
    if "collab_enabled" not in doc:
        return None
    return bool(doc.get("collab_enabled"))


def save_persisted_collab_enabled(enabled: bool, *, repo_root: Path | None = None) -> None:
    root = repo_root or find_repo_root()
    path = collab_settings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"collab_enabled": enabled}, sort_keys=False),
        encoding="utf-8",
    )
