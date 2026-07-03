from __future__ import annotations

import pytest

from memory.user_scope import user_scope_hash


def test_user_scope_hash_stable() -> None:
    h1 = user_scope_hash("alice")
    h2 = user_scope_hash("alice")
    assert h1 == h2
    assert len(h1) == 16


def test_user_scope_hash_requires_user() -> None:
    with pytest.raises(ValueError):
        user_scope_hash("")
