from __future__ import annotations

import hashlib
from pathlib import Path


def user_scope_hash(user_id: str) -> str:
    uid = user_id.strip()
    if not uid:
        raise ValueError("user_id is required")
    return hashlib.sha256(uid.encode("utf-8")).hexdigest()[:16]


def user_memory_index_dir(repo_root: Path, user_id: str, *, tenant_id: str | None = None) -> Path:
    uid = user_id.strip()
    if not uid:
        raise ValueError("user_id is required")
    base = repo_root / "configs" / "memory" / "users" / uid
    if tenant_id:
        return base / f"tenant_{tenant_id.strip()}"
    return base


def memory_retrieval_policy(private: bool = True, project_shared: bool = True) -> dict[str, bool]:
    return {"private": private, "project_shared": project_shared}
