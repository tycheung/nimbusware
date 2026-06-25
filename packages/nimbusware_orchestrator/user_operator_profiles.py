from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nimbusware_env import find_repo_root


def _autopilot_user_path(repo_root: Path, user_id: str) -> Path:
    return repo_root / "configs" / "autopilot" / "users" / f"{user_id.strip()}.yaml"


def _enforcement_user_path(repo_root: Path, user_id: str) -> Path:
    return repo_root / "configs" / "enforcement" / "users" / f"{user_id.strip()}.yaml"


def load_user_autopilot_profile_id(
    user_id: str,
    *,
    repo_root: Path | None = None,
) -> str | None:
    uid = user_id.strip()
    if not uid:
        return None
    root = repo_root or find_repo_root()
    path = _autopilot_user_path(root, uid)
    if not path.is_file():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None
    pid = str(raw.get("profile_id") or raw.get("autopilot_profile_id") or "").strip()
    return pid or None


def save_user_autopilot_profile_id(
    user_id: str,
    profile_id: str,
    *,
    repo_root: Path | None = None,
) -> dict[str, str]:
    uid = user_id.strip()
    pid = profile_id.strip()
    if not uid or not pid:
        raise ValueError("user_id and profile_id required")
    root = repo_root or find_repo_root()
    path = _autopilot_user_path(root, uid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"profile_id": pid}, sort_keys=False), encoding="utf-8")
    return {"user_id": uid, "autopilot_profile_id": pid}


def load_user_enforcement_profile_id(
    user_id: str,
    *,
    repo_root: Path | None = None,
) -> str | None:
    uid = user_id.strip()
    if not uid:
        return None
    root = repo_root or find_repo_root()
    path = _enforcement_user_path(root, uid)
    if not path.is_file():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None
    pid = str(raw.get("profile_id") or raw.get("enforcement_profile_id") or "").strip()
    return pid or None


def save_user_enforcement_profile_id(
    user_id: str,
    profile_id: str,
    *,
    repo_root: Path | None = None,
) -> dict[str, str]:
    uid = user_id.strip()
    pid = profile_id.strip()
    if not uid or not pid:
        raise ValueError("user_id and profile_id required")
    root = repo_root or find_repo_root()
    path = _enforcement_user_path(root, uid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"profile_id": pid}, sort_keys=False), encoding="utf-8")
    return {"user_id": uid, "enforcement_profile_id": pid}


def load_user_operator_profiles(
    user_id: str,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    return {
        "user_id": user_id.strip(),
        "autopilot_profile_id": load_user_autopilot_profile_id(user_id, repo_root=repo_root),
        "enforcement_profile_id": load_user_enforcement_profile_id(user_id, repo_root=repo_root),
    }


def save_user_operator_profiles(
    user_id: str,
    *,
    autopilot_profile_id: str | None = None,
    enforcement_profile_id: str | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    uid = user_id.strip()
    if not uid:
        raise ValueError("user_id required")
    root = repo_root or find_repo_root()
    out = load_user_operator_profiles(uid, repo_root=root)
    if autopilot_profile_id is not None and str(autopilot_profile_id).strip():
        out.update(
            save_user_autopilot_profile_id(uid, str(autopilot_profile_id), repo_root=root),
        )
    if enforcement_profile_id is not None and str(enforcement_profile_id).strip():
        out.update(
            save_user_enforcement_profile_id(uid, str(enforcement_profile_id), repo_root=root),
        )
    return out
