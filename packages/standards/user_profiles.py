from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from env import find_repo_root
from standards.profile import StandardsProfile


@dataclass(frozen=True)
class UserStandardsProfile:
    profile_id: str
    name: str
    facade_id: str | None = None
    bundle_ids: tuple[str, ...] = ()
    connector_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "facade_id": self.facade_id,
            "bundle_ids": list(self.bundle_ids),
            "connector_ids": list(self.connector_ids),
        }


def _profiles_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "standards" / "user_profiles.yaml"


def load_user_standards_profiles(repo_root: Path | None = None) -> dict[str, UserStandardsProfile]:
    path = _profiles_path(repo_root)
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profiles_raw = raw.get("profiles") if isinstance(raw, dict) else None
    if not isinstance(profiles_raw, list):
        return {}
    out: dict[str, UserStandardsProfile] = {}
    for item in profiles_raw:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("profile_id") or item.get("id") or "").strip()
        if not pid:
            continue
        bundles = item.get("bundles")
        connectors = item.get("connectors")
        out[pid] = UserStandardsProfile(
            profile_id=pid,
            name=str(item.get("name") or pid),
            facade_id=str(item.get("facade_id") or "").strip() or None,
            bundle_ids=tuple(str(b) for b in bundles) if isinstance(bundles, list) else (),
            connector_ids=tuple(str(c) for c in connectors) if isinstance(connectors, list) else (),
        )
    return out


def save_user_standards_profiles(
    profiles: dict[str, UserStandardsProfile],
    *,
    repo_root: Path | None = None,
) -> None:
    path = _profiles_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "profiles": [p.to_dict() for p in sorted(profiles.values(), key=lambda x: x.profile_id)],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def upsert_user_standards_profile(
    *,
    profile_id: str,
    name: str,
    facade_id: str | None = None,
    bundle_ids: list[str] | None = None,
    connector_ids: list[str] | None = None,
    repo_root: Path | None = None,
) -> UserStandardsProfile:
    profiles = load_user_standards_profiles(repo_root)
    entry = UserStandardsProfile(
        profile_id=profile_id,
        name=name,
        facade_id=facade_id,
        bundle_ids=tuple(bundle_ids or ()),
        connector_ids=tuple(connector_ids or ()),
    )
    profiles[profile_id] = entry
    save_user_standards_profiles(profiles, repo_root=repo_root)
    return entry


def resolve_user_standards_profile(
    profile_id: str,
    *,
    repo_root: Path | None = None,
) -> StandardsProfile | None:
    entry = load_user_standards_profiles(repo_root).get(profile_id.strip())
    if entry is None:
        return None
    from standards.profile import resolve_standards_profile

    base = resolve_standards_profile(facade_id=entry.facade_id)
    bundles = list(dict.fromkeys([*base.bundle_ids, *entry.bundle_ids]))
    connectors = list(dict.fromkeys([*base.connector_ids, *entry.connector_ids]))
    return StandardsProfile(
        profile_id=entry.profile_id,
        facade_id=entry.facade_id or base.facade_id,
        bundle_ids=tuple(bundles),
        connector_ids=tuple(connectors),
        stream_ids=base.stream_ids,
        verdict_overrides=base.verdict_overrides,
        custom=True,
    )
