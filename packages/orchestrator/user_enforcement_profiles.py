from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml

from env import find_repo_root
from orchestrator.enforcement_profiles import (
    EnforcementProfile,
    resolve_enforcement_profile,
)


@dataclass(frozen=True)
class UserEnforcementProfile:
    profile_id: str
    name: str
    level: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "level": self.level,
        }


def _profiles_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "enforcement" / "user_profiles.yaml"


def load_user_enforcement_profiles(
    repo_root: Path | None = None,
) -> dict[str, UserEnforcementProfile]:
    path = _profiles_path(repo_root)
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profiles_raw = raw.get("profiles") if isinstance(raw, dict) else None
    if not isinstance(profiles_raw, list):
        return {}
    out: dict[str, UserEnforcementProfile] = {}
    for item in profiles_raw:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("profile_id") or item.get("id") or "").strip()
        if not pid:
            continue
        out[pid] = UserEnforcementProfile(
            profile_id=pid,
            name=str(item.get("name") or pid),
            level=int(item.get("level") or 5),
        )
    return out


def save_user_enforcement_profiles(
    profiles: dict[str, UserEnforcementProfile],
    *,
    repo_root: Path | None = None,
) -> None:
    path = _profiles_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "profiles": [p.to_dict() for p in sorted(profiles.values(), key=lambda x: x.profile_id)],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def upsert_user_enforcement_profile(
    *,
    profile_id: str,
    name: str,
    level: int,
    repo_root: Path | None = None,
) -> UserEnforcementProfile:
    profiles = load_user_enforcement_profiles(repo_root)
    entry = UserEnforcementProfile(profile_id=profile_id, name=name, level=level)
    profiles[profile_id] = entry
    save_user_enforcement_profiles(profiles, repo_root=repo_root)
    return entry


def resolve_user_enforcement_profile(
    profile_id: str,
    *,
    repo_root: Path | None = None,
) -> EnforcementProfile | None:
    entry = load_user_enforcement_profiles(repo_root).get(profile_id)
    if entry is None:
        return None
    return resolve_enforcement_profile(level=entry.level)


def apply_user_enforcement_at_run_start(
    store: Any,
    run_id: UUID,
    profile_id: str,
    *,
    repo_root: Path | None = None,
) -> EnforcementProfile | None:
    from uuid import UUID as UUIDType

    from iam.context import get_auth_context
    from orchestrator.enforcement_profiles import persist_run_enforcement

    profile = resolve_user_enforcement_profile(profile_id.strip(), repo_root=repo_root)
    if profile is None:
        return None
    rid = run_id if isinstance(run_id, UUIDType) else UUIDType(str(run_id))
    ctx = get_auth_context()
    return persist_run_enforcement(
        store,
        rid,
        profile,
        tenant_slug=ctx.tenant_slug if ctx else None,
        repo_root=repo_root,
    )
