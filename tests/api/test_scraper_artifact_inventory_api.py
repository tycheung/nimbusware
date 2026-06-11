from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nimbusware_env import find_repo_root

os.environ.setdefault(
    "NIMBUSWARE_REPO_ROOT", str(find_repo_root(start=Path(__file__).resolve().parents[1]))
)
os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault(
    "NIMBUSWARE_ADMIN_TOKEN", "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
)

from nimbusware_api.app import app  # noqa: E402
from nimbusware_orchestrator.scraper_artifacts import scraper_artifact_inventory  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_scraper_artifact_inventory_helper_missing_dir(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    inv = scraper_artifact_inventory(missing)
    assert inv["exists"] is False
    assert inv["file_count"] == 0
    assert inv["entries"] == []
    assert inv["truncated"] is False
    assert inv["retention_stale_file_count"] == 0
    assert inv["retention_stale_bytes"] == 0
    assert inv["storage_backend"] == "local"
    assert inv["object_store_configured"] is False
    assert inv["object_store_ready"] is False
    assert inv["object_store_timeout_seconds"] == 30
    assert inv["object_store_delete_max_attempts"] == 1
    assert inv["object_store_prune_requested"] is False
    assert inv["object_store_prune_effective"] is False
    assert inv["retention_execution_mode"] == "local_only"
    assert inv["retention_alert_level"] == "none"


def test_scraper_artifact_inventory_helper_counts_files(tmp_path: Path) -> None:
    base = tmp_path / "cache"
    (base / "a").mkdir(parents=True)
    (base / "a" / "one.bin").write_bytes(b"abc")
    (base / "b.txt").write_text("x")
    inv = scraper_artifact_inventory(base, max_entries=10)
    assert inv["exists"] is True
    assert inv["file_count"] == 2
    assert inv["total_bytes"] == 4
    relpaths = {e["relpath"] for e in inv["entries"]}
    assert "a/one.bin" in relpaths
    assert "b.txt" in relpaths
    assert isinstance(inv["oldest_mtime_iso"], str)
    assert isinstance(inv["newest_mtime_iso"], str)


def test_scraper_artifact_inventory_api(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    base = tmp_path / "artifacts"
    sub = base / "run-1"
    sub.mkdir(parents=True)
    (sub / "page.html").write_text("<html/>")
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_DIR", str(base))
    r = client.get("/v1/scraper-artifacts/inventory", params={"max_entries": 50})
    assert r.status_code == 200
    body = r.json()
    assert body["exists"] is True
    assert body["file_count"] == 1
    assert body["entries"][0]["relpath"] == "run-1/page.html"
    assert body["total_bytes"] > 0
    assert body["oldest_mtime_iso"] is not None
    assert body["newest_mtime_iso"] is not None
    assert body["retention_stale_file_count"] >= 0
    assert body["retention_stale_bytes"] >= 0
    assert body["storage_backend"] == "local"
    assert body["object_store_configured"] is False
    assert body["object_store_ready"] is False
    assert body["object_store_timeout_seconds"] == 30
    assert body["object_store_delete_max_attempts"] == 1
    assert body["object_store_prune_requested"] is False
    assert body["object_store_prune_effective"] is False
    assert body["retention_execution_mode"] == "local_only"
    assert body["retention_alert_level"] == "none"


def test_scraper_artifact_inventory_retention_alert_stale_present(
    tmp_path: Path,
) -> None:
    base = tmp_path / "cache"
    base.mkdir(parents=True)
    stale = base / "old.bin"
    stale.write_bytes(b"x" * 100)
    import os
    import time

    old = time.time() - 30 * 86400
    os.utime(stale, (old, old))
    inv = scraper_artifact_inventory(base, retention_max_age_days=7)
    assert inv["retention_stale_file_count"] == 1
    assert inv["retention_alert_level"] == "stale_present"


def test_scraper_artifact_inventory_object_store_ready_signals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_URL",
        "https://s3.example.com",
    )
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_BUCKET", "nimbusware-artifacts")
    from nimbusware_orchestrator.scraper_artifacts import scraper_artifact_storage_backend_signals

    sig = scraper_artifact_storage_backend_signals()
    assert sig["storage_backend"] == "object_store_ready"
    assert sig["object_store_configured"] is True
    assert sig["object_store_ready"] is True
    assert sig["object_store_timeout_seconds"] == 30
    assert sig["object_store_delete_max_attempts"] == 1
    assert sig["object_store_prune_requested"] is False
    assert sig["object_store_prune_effective"] is False


def test_scraper_artifact_inventory_object_store_prune_requested_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_PRUNE", "1")
    monkeypatch.setenv(
        "NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_URL",
        "https://s3.example.com",
    )
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_BUCKET", "nimbusware-artifacts")
    from nimbusware_orchestrator.scraper_artifacts import scraper_artifact_storage_backend_signals

    sig = scraper_artifact_storage_backend_signals()
    assert sig["object_store_prune_requested"] is True
    assert sig["object_store_prune_effective"] is True


def test_scraper_artifact_inventory_object_store_delete_tuning_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_URL",
        "https://s3.example.com",
    )
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_BUCKET", "nimbusware-artifacts")
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_TIMEOUT_SECONDS", "17")
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_DELETE_MAX_ATTEMPTS", "3")
    from nimbusware_orchestrator.scraper_artifacts import scraper_artifact_storage_backend_signals

    sig = scraper_artifact_storage_backend_signals()
    assert sig["object_store_timeout_seconds"] == 17
    assert sig["object_store_delete_max_attempts"] == 3


def test_scraper_artifact_inventory_api_includes_retention_days(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    base = tmp_path / "artifacts"
    base.mkdir(parents=True)
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_DIR", str(base))
    monkeypatch.setenv("NIMBUSWARE_SCRAPER_ARTIFACT_MAX_AGE_DAYS", "14")
    r = client.get("/v1/scraper-artifacts/inventory", params={"max_entries": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["retention_max_age_days"] == 14
    assert body["retention_stale_file_count"] >= 0
    assert body["retention_stale_bytes"] >= 0
