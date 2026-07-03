from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from env.edition import DEFAULT_EDITION, ENTERPRISE_EDITION, ENV_EDITION
from orchestrator.scraper.artifacts import (
    persist_scraper_artifact,
    prune_scraper_artifacts,
    scraper_artifact_inventory,
    scraper_artifact_storage_backend_signals,
)
from orchestrator.scraper.object_store import (
    object_store_list_artifacts,
    object_store_primary_enabled,
    object_store_put_artifact,
)


def test_object_store_primary_disabled_on_individual(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, DEFAULT_EDITION)
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_PRIMARY", "1")
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_URL", "file:///tmp/os")
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_BUCKET", "b")
    assert not object_store_primary_enabled()


def test_file_backend_put_list_inventory_primary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_PRIMARY", "1")
    store_root = tmp_path / "object_store"
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_URL", store_root.as_uri())
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_BUCKET", "artifacts")

    assert object_store_primary_enabled()
    put = object_store_put_artifact("run-a/page.bin", b"<html/>")
    assert put["stored"] is True

    listed = object_store_list_artifacts(max_entries=10)
    assert any(e["relpath"] == "run-a/page.bin" for e in listed)

    local_base = tmp_path / "local_cache"
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_DIR", str(local_base))
    inv = scraper_artifact_inventory(local_base, max_entries=10)
    assert inv["storage_backend"] == "object_store_primary"
    assert inv["file_count"] >= 1
    assert inv["retention_execution_mode"] == "object_store_primary"


def test_persist_scraper_artifact_primary_without_local_mirror(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_PRIMARY", "1")
    store_root = tmp_path / "object_store"
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_URL", store_root.as_uri())
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_BUCKET", "artifacts")
    monkeypatch.delenv("NIMBUSWARE_SCRAPER_ARTIFACT_LOCAL_MIRROR", raising=False)

    meta = persist_scraper_artifact(tmp_path, uuid4(), 0, b"payload-bytes", 1024)
    assert meta["storage_authority"] == "object_store_primary"
    assert object_store_list_artifacts(max_entries=5)


def test_prune_primary_file_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from datetime import datetime, timedelta, timezone

    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_PRIMARY", "1")
    store_root = tmp_path / "object_store"
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_URL", store_root.as_uri())
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_BUCKET", "artifacts")

    now = datetime.now(timezone.utc)
    from orchestrator.scraper.object_store import _file_object_path

    put = object_store_put_artifact("stale/old.bin", b"x")
    assert put["stored"] is True
    listed_before = object_store_list_artifacts(max_entries=20)
    assert any(e["relpath"] == "stale/old.bin" for e in listed_before)
    stale_path = _file_object_path("stale/old.bin")
    assert stale_path is not None
    old = (now - timedelta(days=30)).timestamp()
    import os

    os.utime(stale_path, (old, old))

    result = prune_scraper_artifacts(
        tmp_path / "unused_local",
        max_age_days=7,
        now=now,
    )
    assert result["retention_execution_mode"] == "object_store_primary"
    assert result["retention_stale_file_count"] >= 1
    assert result["local_removed"] >= 1
    assert stale_path is not None and not stale_path.is_file()


def test_storage_signals_primary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_PRIMARY", "1")
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_URL", "file:///tmp/x")
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_BUCKET", "b")
    sig = scraper_artifact_storage_backend_signals()
    assert sig["storage_backend"] == "object_store_primary"
    assert sig["object_store_primary"] is True
