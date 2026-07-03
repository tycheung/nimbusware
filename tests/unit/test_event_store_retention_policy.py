from __future__ import annotations

import os

import pytest

from store.retention_policy import event_store_retention_days


def test_event_store_retention_disabled_by_default() -> None:
    os.environ.pop("NIMBUSWARE_EVENT_STORE_RETENTION_DAYS", None)
    assert event_store_retention_days() is None


def test_event_store_retention_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EVENT_STORE_RETENTION_DAYS", "180")
    assert event_store_retention_days() == 180


def test_purge_eligible_before_respects_window(monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import datetime, timezone

    from store.retention_policy import purge_eligible_before

    monkeypatch.setenv("NIMBUSWARE_EVENT_STORE_RETENTION_DAYS", "30")
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    cutoff = purge_eligible_before(now=now)
    assert cutoff is not None
    assert (now - cutoff).days == 30
