from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.autopilot_profiles import (
    AutopilotProfile,
    resolve_autopilot_profile,
)


@dataclass(frozen=True)
class UserAutopilotProfile:
    profile_id: str
    name: str
    level: int
    checkpoints: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "level": self.level,
            "checkpoints": list(self.checkpoints),
        }


def _profiles_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "autopilot" / "user_profiles.yaml"


def load_user_autopilot_profiles(repo_root: Path | None = None) -> dict[str, UserAutopilotProfile]:
    path = _profiles_path(repo_root)
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profiles_raw = raw.get("profiles") if isinstance(raw, dict) else None
    if not isinstance(profiles_raw, list):
        return {}
    out: dict[str, UserAutopilotProfile] = {}
    for item in profiles_raw:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("profile_id") or item.get("id") or "").strip()
        if not pid:
            continue
        cps = item.get("checkpoints")
        checkpoints = tuple(str(c) for c in cps) if isinstance(cps, list) else ()
        out[pid] = UserAutopilotProfile(
            profile_id=pid,
            name=str(item.get("name") or pid),
            level=int(item.get("level") or 5),
            checkpoints=checkpoints,
        )
    return out


def save_user_autopilot_profiles(
    profiles: dict[str, UserAutopilotProfile],
    *,
    repo_root: Path | None = None,
) -> None:
    path = _profiles_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "profiles": [p.to_dict() for p in sorted(profiles.values(), key=lambda x: x.profile_id)],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def upsert_user_autopilot_profile(
    *,
    profile_id: str,
    name: str,
    level: int,
    checkpoints: set[str] | list[str],
    repo_root: Path | None = None,
) -> UserAutopilotProfile:
    profiles = load_user_autopilot_profiles(repo_root)
    entry = UserAutopilotProfile(
        profile_id=profile_id,
        name=name,
        level=level,
        checkpoints=tuple(sorted(set(str(c) for c in checkpoints))),
    )
    profiles[profile_id] = entry
    save_user_autopilot_profiles(profiles, repo_root=repo_root)
    return entry


def resolve_user_autopilot_profile(
    profile_id: str,
    *,
    repo_root: Path | None = None,
) -> AutopilotProfile | None:
    entry = load_user_autopilot_profiles(repo_root).get(profile_id)
    if entry is None:
        return None
    return resolve_autopilot_profile(
        level=entry.level,
        custom_checkpoints=set(entry.checkpoints) if entry.checkpoints else None,
    )
