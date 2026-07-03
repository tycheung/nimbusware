from __future__ import annotations

import pytest

from auth.crypto import hash_password, verify_password
from auth.store import InMemoryUserStore


def test_password_hash_roundtrip() -> None:
    digest = hash_password("correct-horse-battery")
    assert verify_password("correct-horse-battery", digest)
    assert not verify_password("wrong", digest)


def test_first_user_becomes_owner() -> None:
    store = InMemoryUserStore()
    owner = store.create_user(
        username="owner",
        password="password1234",
        display_name="Owner",
    )
    assert owner.is_owner is True
    guest = store.create_user(username="guest", password="password1234")
    assert guest.is_owner is False


def test_username_unique() -> None:
    store = InMemoryUserStore()
    store.create_user(username="alice", password="password1234")
    with pytest.raises(ValueError, match="username_taken"):
        store.create_user(username="Alice", password="password1234")


def test_search_users_prefix() -> None:
    store = InMemoryUserStore()
    store.create_user(username="alice", password="password1234", display_name="Alice A")
    store.create_user(username="bob", password="password1234", display_name="Bob B")
    hits = store.search_users(query="ali")
    assert len(hits) == 1
    assert hits[0].username == "alice"
