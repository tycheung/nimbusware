from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from env import find_repo_root


def _standards_root(start: Path | None = None) -> Path:
    return find_repo_root(start=start) / "configs" / "standards"


@lru_cache(maxsize=1)
def load_streams_config() -> dict[str, Any]:
    path = _standards_root() / "streams.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


@lru_cache(maxsize=1)
def load_registry_config() -> dict[str, Any]:
    path = _standards_root() / "registry.yaml"
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def stream_ids() -> list[str]:
    streams = load_streams_config().get("streams")
    if not isinstance(streams, dict):
        return []
    return sorted(str(k) for k in streams)


def profile_stream_ids(profile_id: str) -> list[str]:
    profiles = load_streams_config().get("profiles")
    if not isinstance(profiles, dict):
        return []
    profile = profiles.get(profile_id)
    if not isinstance(profile, dict):
        return []
    streams = profile.get("streams")
    if not isinstance(streams, list):
        return []
    return [str(s) for s in streams]


def stream_checks(stream_id: str) -> list[dict[str, Any]]:
    streams = load_streams_config().get("streams")
    if not isinstance(streams, dict):
        return []
    block = streams.get(stream_id)
    if not isinstance(block, dict):
        return []
    checks = block.get("checks")
    if not isinstance(checks, list):
        return []
    return [c for c in checks if isinstance(c, dict)]


def load_bundle_manifest(bundle_id: str) -> dict[str, Any] | None:
    bundles = load_registry_config().get("bundles")
    if not isinstance(bundles, dict):
        return None
    entry = bundles.get(bundle_id)
    if not isinstance(entry, dict):
        return None
    path_raw = entry.get("path")
    if not isinstance(path_raw, str) or not path_raw.strip():
        return None
    path = _standards_root() / path_raw
    if not path.is_file():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else None


def load_facade_manifest(facade_id: str) -> dict[str, Any] | None:
    facades = load_registry_config().get("facades")
    if not isinstance(facades, dict):
        return None
    entry = facades.get(facade_id)
    if not isinstance(entry, dict):
        return None
    path_raw = entry.get("path")
    if not isinstance(path_raw, str) or not path_raw.strip():
        return None
    path = _standards_root() / path_raw
    if not path.is_file():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else None


def mart_catalog() -> dict[str, Any]:
    reg = load_registry_config()
    return {
        "streams": stream_ids(),
        "bundles": reg.get("bundles") if isinstance(reg.get("bundles"), dict) else {},
        "facades": reg.get("facades") if isinstance(reg.get("facades"), dict) else {},
        "connectors": reg.get("connectors") if isinstance(reg.get("connectors"), dict) else {},
        "tiers": reg.get("tiers") if isinstance(reg.get("tiers"), dict) else {},
    }
