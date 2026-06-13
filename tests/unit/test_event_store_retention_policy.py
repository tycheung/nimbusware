from __future__ import annotations

import os

import pytest

from nimbusware_store.retention_policy import event_store_retention_days


def test_event_store_retention_disabled_by_default() -> None:
    os.environ.pop("NIMBUSWARE_EVENT_STORE_RETENTION_DAYS", None)
    assert event_store_retention_days() is None


def test_event_store_retention_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EVENT_STORE_RETENTION_DAYS", "180")
    assert event_store_retention_days() == 180
