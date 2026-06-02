from __future__ import annotations

import os
import uuid

import pytest

from nimbusware_config.store import PostgresConfigStore

pytestmark = pytest.mark.integration


def _url() -> str:
    u = os.environ.get("NIMBUSWARE_DATABASE_URL")
    if not u:
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")
    return u


def test_postgres_config_store_upsert_get_round_trip() -> None:
    store = PostgresConfigStore(_url())
    key = f"lane-w3-{uuid.uuid4().hex[:8]}"
    row = store.upsert("workflows", key, {"stages": [], "lane": "w3"})
    assert row.version >= 1
    got = store.get("workflows", key)
    assert got is not None
    assert got.content.get("lane") == "w3"
    assert store.delete("workflows", key) is True


def test_postgres_config_store_expected_version_increments() -> None:
    store = PostgresConfigStore(_url())
    key = f"lane-w3-ver-{uuid.uuid4().hex[:8]}"
    first = store.upsert("workflows", key, {"stages": [], "v": 1})
    second = store.upsert(
        "workflows",
        key,
        {"stages": [], "v": 2},
        expected_version=first.version,
    )
    assert second.version == first.version + 1
    assert second.content.get("v") == 2
    assert store.delete("workflows", key) is True
