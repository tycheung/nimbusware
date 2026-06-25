from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_memory.user_scope import memory_retrieval_policy, user_memory_index_dir


def test_user_memory_index_dir() -> None:
    root = Path("/tmp/nimbusware")
    path = user_memory_index_dir(root, "alice")
    assert path == root / "configs" / "memory" / "users" / "alice"


def test_user_memory_index_dir_requires_user() -> None:
    with pytest.raises(ValueError):
        user_memory_index_dir(Path("/tmp"), "")


def test_memory_retrieval_policy_defaults() -> None:
    pol = memory_retrieval_policy()
    assert pol["private"] is True
    assert pol["project_shared"] is True
