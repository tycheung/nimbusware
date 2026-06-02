from __future__ import annotations

import pytest

from nimbusware_config.store import InMemoryConfigStore


def test_in_memory_upsert_get_round_trip() -> None:
    store = InMemoryConfigStore()
    row = store.upsert("personas", "shelves", {"version": 1, "business_area": []})
    assert row.namespace == "personas"
    assert row.document_key == "shelves"
    assert row.version == 1
    assert row.content["version"] == 1
    assert len(row.content_sha256_16) == 16

    got = store.get("personas", "shelves")
    assert got is not None
    assert got.version == 1
    assert got.content == row.content


def test_in_memory_rejects_non_object_content() -> None:
    store = InMemoryConfigStore()
    with pytest.raises(ValueError, match="mapping"):
        store.upsert("personas", "shelves", [])  # type: ignore[arg-type]


def test_in_memory_expected_version_conflict() -> None:
    store = InMemoryConfigStore()
    store.upsert("roles", "registry", {"roles": [], "version": 1})
    with pytest.raises(ValueError, match="version conflict"):
        store.upsert(
            "roles",
            "registry",
            {"roles": [], "version": 2},
            expected_version=99,
        )


def test_in_memory_list_keys_and_delete() -> None:
    store = InMemoryConfigStore()
    store.upsert("workflows", "default", {"stages": []})
    store.upsert("workflows", "custom", {"stages": []})
    assert store.list_keys("workflows") == ["custom", "default"]
    assert store.delete("workflows", "custom") is True
    assert store.list_keys("workflows") == ["default"]
