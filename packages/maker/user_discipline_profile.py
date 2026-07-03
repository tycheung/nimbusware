from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from env import find_repo_root
from maker.collab_disciplines import normalize_discipline


def _user_path(repo_root: Path, user_id: str) -> Path:
    return repo_root / "configs" / "collab" / "users" / f"{user_id.strip()}.yaml"


def load_user_discipline_profile(
    user_id: str,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    uid = user_id.strip()
    if not uid:
        return {"user_id": "", "default_discipline": None}
    root = repo_root or find_repo_root()
    path = _user_path(root, uid)
    if not path.is_file():
        return {"user_id": uid, "default_discipline": None}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {"user_id": uid, "default_discipline": None}
    discipline = normalize_discipline(str(raw.get("default_discipline") or ""), repo_root=root)
    return {"user_id": uid, "default_discipline": discipline}


def save_user_discipline_profile(
    user_id: str,
    *,
    default_discipline: str | None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    uid = user_id.strip()
    if not uid:
        raise ValueError("user_id required")
    root = repo_root or find_repo_root()
    discipline = (
        normalize_discipline(default_discipline or "", repo_root=root)
        if default_discipline
        else None
    )
    path = _user_path(root, uid)
    path.parent.mkdir(parents=True, exist_ok=True)
    if discipline:
        path.write_text(
            yaml.safe_dump({"default_discipline": discipline}, sort_keys=False),
            encoding="utf-8",
        )
    elif path.is_file():
        path.unlink()
    return {"user_id": uid, "default_discipline": discipline}
