"""Peel stub — local memory capability removed (sak413). Use memory_bridge / sak."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def memory_retrieval_policy(*args: Any, **kwargs: Any) -> dict[str, bool]:
    """Default retrieval scope after local peel (broker path preferred)."""
    return {"private": True, "project_shared": True}


def user_memory_index_dir(repo_root: Path, user_id: str) -> Path:
    uid = str(user_id or "").strip()
    if not uid:
        raise ValueError("user_id required")
    return Path(repo_root) / "configs" / "memory" / "users" / uid


def __getattr__(name: str):
    def _gone(*args, **kwargs):
        raise RuntimeError(
            f"{__name__}.{name} removed (sak413); use agent_tools.memory_bridge / sak memory_*"
        )

    _gone.__name__ = name
    return _gone
