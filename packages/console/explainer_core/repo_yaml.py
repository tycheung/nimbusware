from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def relative_under(repo_root: Path, path: Path) -> str:
    root = repo_root.resolve()
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path.resolve())


def json_safe_yaml_fragment(raw: object) -> object:
    if raw is None or isinstance(raw, (bool, int, float, str)):
        return raw
    if isinstance(raw, dict):
        out: dict[str, Any] = {}
        for key, value in raw.items():
            sk = key if isinstance(key, str) else str(key)
            out[sk] = json_safe_yaml_fragment(value)
        return out
    if isinstance(raw, list):
        return [json_safe_yaml_fragment(item) for item in raw]
    return str(raw)


def mtime_iso_utc(path: Path) -> str | None:
    try:
        mtime_ns = int(path.stat().st_mtime_ns)
    except OSError:
        return None
    return datetime.fromtimestamp(mtime_ns / 1e9, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ",
    )
