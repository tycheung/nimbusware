from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from store.retention_policy import (
    legal_hold_enabled,
    purge_execute_enabled,
)

_PURGE_SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "database" / "purge_event_store_retention.py"
)


def _purge_main():
    spec = importlib.util.spec_from_file_location("purge_event_store_retention", _PURGE_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main


def test_legal_hold_blocks_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_EVENT_STORE_LEGAL_HOLD", raising=False)
    assert legal_hold_enabled() is False


def test_legal_hold_truthy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EVENT_STORE_LEGAL_HOLD", "1")
    assert legal_hold_enabled() is True


def test_purge_execute_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_EVENT_STORE_PURGE_EXECUTE", raising=False)
    assert purge_execute_enabled() is False


def test_purge_execute_truthy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EVENT_STORE_PURGE_EXECUTE", "1")
    assert purge_execute_enabled() is True


def test_purge_script_dry_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("NIMBUSWARE_DATABASE_URL", "postgresql://localhost/test")
    monkeypatch.setenv("NIMBUSWARE_EVENT_STORE_RETENTION_DAYS", "90")
    monkeypatch.delenv("NIMBUSWARE_EVENT_STORE_LEGAL_HOLD", raising=False)
    monkeypatch.setattr("sys.argv", ["purge_event_store_retention.py"])

    cutoff = datetime(2026, 3, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "store.retention_policy.purge_eligible_before",
        lambda *, now=None: cutoff,
    )
    monkeypatch.setattr(
        "store.retention_policy.purge_blocked_by_legal_hold",
        lambda tenant_slug="default": False,
    )

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (42,)
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr("psycopg.connect", lambda _url: conn)

    assert _purge_main()() == 0
    out = capsys.readouterr().out
    assert "Eligible rows before" in out
    assert "42" in out
    assert "Dry-run only" in out


def test_purge_script_legal_hold_skips(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("NIMBUSWARE_DATABASE_URL", "postgresql://localhost/test")
    monkeypatch.setenv("NIMBUSWARE_EVENT_STORE_LEGAL_HOLD", "true")
    monkeypatch.setattr("sys.argv", ["purge_event_store_retention.py"])
    monkeypatch.setattr("psycopg.connect", MagicMock())

    assert _purge_main()() == 0
    assert "Legal hold active" in capsys.readouterr().out
