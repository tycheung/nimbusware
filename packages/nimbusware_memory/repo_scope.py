from __future__ import annotations

import hashlib
from pathlib import Path

from nimbusware_env.env_flags import env_str


def repo_scope_hash(repo_root: Path) -> str:
    root = repo_root.resolve()
    raw = str(root).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def resolve_repo_root(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env = env_str("NIMBUSWARE_REPO_ROOT")
    if env:
        return Path(env).resolve()
    return Path(".").resolve()
