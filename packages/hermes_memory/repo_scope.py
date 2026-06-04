"""Repo/workspace scope key for memory indexes."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


def repo_scope_hash(repo_root: Path) -> str:
    """Stable scope id for ``NIMBUSWARE_REPO_ROOT`` (16 hex chars)."""
    root = repo_root.resolve()
    raw = str(root).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def resolve_repo_root(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env = os.environ.get("NIMBUSWARE_REPO_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    return Path(".").resolve()
