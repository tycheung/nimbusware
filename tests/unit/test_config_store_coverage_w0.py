from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from nimbusware_config import keys
from nimbusware_config.flags import config_from_db_enabled, config_notify_enabled
from nimbusware_config.store import (
    InMemoryConfigStore,
    PostgresConfigStore,
    _content_digest,
    _maybe_publish_config_notify,
    _row_from_record,
)


def test_config_key_constants() -> None:
    assert keys.NS_WORKFLOWS == "workflows"
    assert keys.KEY_MODEL_ROUTING == "model-routing"


def test_config_flags_callable() -> None:
    assert isinstance(config_from_db_enabled(), bool)
    assert isinstance(config_notify_enabled(), bool)


def test_content_digest_stable() -> None:
    a = _content_digest({"b": 2, "a": 1})
    b = _content_digest({"a": 1, "b": 2})
    assert a == b
    assert len(a) == 16


def test_row_from_record_parses_datetime() -> None:
    ts = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    row = _row_from_record(
        {
            "namespace": "workflows",
            "document_key": "default",
            "version": 2,
            "content": {"stages": []},
            "content_sha256_16": "abc",
            "updated_at": ts,
        },
    )
    assert row.namespace == "workflows"
    assert row.version == 2
    assert row.updated_at == ts


def test_row_from_record_rejects_non_object_content() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        _row_from_record(
            {
                "namespace": "x",
                "document_key": "y",
                "version": 1,
                "content": [],
                "content_sha256_16": "abc",
            },
        )


def test_maybe_publish_config_notify_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("nimbusware_config.flags.config_notify_enabled", lambda: False)
    _maybe_publish_config_notify("ns", "key", 1)


def test_maybe_publish_config_notify_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    hub = MagicMock()
    monkeypatch.setattr("nimbusware_config.flags.config_notify_enabled", lambda: True)
    monkeypatch.setattr("nimbusware_config.notify.get_config_notify_hub", lambda: hub)
    _maybe_publish_config_notify("roles", "registry", 3)
    hub.publish_local.assert_called_once_with(namespace="roles", document_key="registry", version=3)


def test_in_memory_upsert_bumps_version() -> None:
    store = InMemoryConfigStore()
    first = store.upsert("workflows", "default", {"v": 1})
    second = store.upsert("workflows", "default", {"v": 2})
    assert first.version == 1
    assert second.version == 2


class _FakeCursor:
    def __init__(self, fetchone: Any = None, fetchall: Any = None, rowcount: int = 0) -> None:
        self._fetchone = fetchone
        self._fetchall = fetchall or []
        self.rowcount = rowcount

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, *args: object, **kwargs: object) -> None:
        return None

    def fetchone(self) -> Any:
        return self._fetchone

    def fetchall(self) -> list[Any]:
        return self._fetchall


class _FakeConn:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def cursor(self, **kwargs: object) -> _FakeCursor:
        return self._cursor

    def commit(self) -> None:
        return None


def test_postgres_config_store_get_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    cur = _FakeCursor(fetchone=None)
    monkeypatch.setattr("nimbusware_config.store.psycopg.connect", lambda _: _FakeConn(cur))
    store = PostgresConfigStore("postgresql://x")
    assert store.get("workflows", "missing") is None


def test_postgres_config_store_get_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = {
        "namespace": "workflows",
        "document_key": "default",
        "version": 1,
        "content": {"stages": []},
        "content_sha256_16": _content_digest({"stages": []}),
        "updated_at": None,
    }
    cur = _FakeCursor(fetchone=rec)
    monkeypatch.setattr("nimbusware_config.store.psycopg.connect", lambda _: _FakeConn(cur))
    store = PostgresConfigStore("postgresql://x")
    row = store.get("workflows", "default")
    assert row is not None
    assert row.document_key == "default"


def test_postgres_config_store_list_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    cur = _FakeCursor(fetchall=[("a",), ("b",)])
    monkeypatch.setattr("nimbusware_config.store.psycopg.connect", lambda _: _FakeConn(cur))
    store = PostgresConfigStore("postgresql://x")
    assert store.list_keys("workflows") == ["a", "b"]


def test_postgres_config_store_delete(monkeypatch: pytest.MonkeyPatch) -> None:
    cur = _FakeCursor(rowcount=1)
    monkeypatch.setattr("nimbusware_config.store.psycopg.connect", lambda _: _FakeConn(cur))
    store = PostgresConfigStore("postgresql://x")
    assert store.delete("workflows", "default") is True


def test_postgres_config_store_upsert_insert(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = {
        "namespace": "workflows",
        "document_key": "default",
        "version": 1,
        "content": {"stages": []},
        "content_sha256_16": _content_digest({"stages": []}),
        "updated_at": datetime.now(timezone.utc),
    }
    cur = _FakeCursor(fetchone=rec)
    monkeypatch.setattr("nimbusware_config.store.psycopg.connect", lambda _: _FakeConn(cur))
    with patch("nimbusware_config.store._maybe_publish_config_notify"):
        store = PostgresConfigStore("postgresql://x")
        row = store.upsert("workflows", "default", {"stages": []})
    assert row.version == 1


def test_postgres_config_store_upsert_version_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    cur = _FakeCursor(fetchone=None)
    monkeypatch.setattr("nimbusware_config.store.psycopg.connect", lambda _: _FakeConn(cur))
    store = PostgresConfigStore("postgresql://x")
    with pytest.raises(ValueError, match="version conflict"):
        store.upsert("workflows", "default", {"x": 1}, expected_version=99)


def test_postgres_config_store_rejects_non_mapping() -> None:
    store = PostgresConfigStore("postgresql://x")
    with pytest.raises(ValueError, match="mapping"):
        store.upsert("workflows", "default", [])  # type: ignore[arg-type]
