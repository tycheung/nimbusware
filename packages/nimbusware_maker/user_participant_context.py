from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nimbusware_env import find_repo_root


def _user_path(repo_root: Path, user_id: str) -> Path:
    return repo_root / "configs" / "collab" / "users" / f"{user_id.strip()}_context.yaml"


def load_user_participant_context(
    user_id: str,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    uid = user_id.strip()
    if not uid:
        return {"user_id": "", "expertise_bullets": []}
    root = repo_root or find_repo_root()
    path = _user_path(root, uid)
    if not path.is_file():
        return {"user_id": uid, "expertise_bullets": []}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {"user_id": uid, "expertise_bullets": []}
    bullets = raw.get("expertise_bullets")
    if not isinstance(bullets, list):
        bullets = []
    cleaned = [str(b).strip() for b in bullets if str(b).strip()][:8]
    return {"user_id": uid, "expertise_bullets": cleaned}


def save_user_participant_context(
    user_id: str,
    *,
    expertise_bullets: list[str],
    repo_root: Path | None = None,
) -> dict[str, Any]:
    uid = user_id.strip()
    if not uid:
        raise ValueError("user_id required")
    root = repo_root or find_repo_root()
    cleaned = [str(b).strip() for b in expertise_bullets if str(b).strip()][:8]
    path = _user_path(root, uid)
    path.parent.mkdir(parents=True, exist_ok=True)
    if cleaned:
        path.write_text(
            yaml.safe_dump({"expertise_bullets": cleaned}, sort_keys=False),
            encoding="utf-8",
        )
    elif path.is_file():
        path.unlink()
    return {"user_id": uid, "expertise_bullets": cleaned}
