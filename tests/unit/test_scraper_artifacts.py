"""Tests for scraper artifact retention helpers."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hermes_orchestrator.scraper_artifacts import (
    prune_scraper_artifacts,
    resolve_scraper_artifact_base_dir,
)


def test_resolve_artifact_dir_env_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    art = tmp_path / "custom_art"
    monkeypatch.setenv("HERMES_SCRAPER_ARTIFACT_DIR", str(art))
    assert resolve_scraper_artifact_base_dir(tmp_path) == art.resolve()


def test_resolve_artifact_dir_default_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HERMES_SCRAPER_ARTIFACT_DIR", raising=False)
    want = (tmp_path / ".cache" / "hermes_scraper").resolve()
    assert resolve_scraper_artifact_base_dir(tmp_path) == want


def test_prune_scraper_artifacts_dry_run_counts_without_deleting(tmp_path: Path) -> None:
    base = tmp_path / "hermes_scraper"
    run_dir = base / "00000000-0000-4000-8000-000000000001"
    run_dir.mkdir(parents=True)
    stale = run_dir / "url00_deadbeef.bin"
    stale.write_bytes(b"x")
    old = time.time() - 10 * 86400
    os.utime(stale, (old, old))

    fresh = run_dir / "url01_cafebabe.bin"
    fresh.write_bytes(b"y")

    now = datetime.now(timezone.utc)
    count = prune_scraper_artifacts(base, max_age_days=7, now=now, dry_run=True)["local_removed"]
    assert count == 1
    assert stale.is_file()
    assert fresh.is_file()


def test_prune_scraper_artifacts_removes_stale_files(tmp_path: Path) -> None:
    base = tmp_path / "hermes_scraper"
    run_dir = base / "00000000-0000-4000-8000-000000000001"
    run_dir.mkdir(parents=True)
    stale = run_dir / "url00_deadbeef.bin"
    stale.write_bytes(b"x")
    old = time.time() - 10 * 86400
    os.utime(stale, (old, old))

    fresh = run_dir / "url01_cafebabe.bin"
    fresh.write_bytes(b"y")

    now = datetime.now(timezone.utc)
    removed = prune_scraper_artifacts(base, max_age_days=7, now=now)["local_removed"]
    assert removed == 1
    assert not stale.exists()
    assert fresh.is_file()


def test_prune_scraper_artifacts_missing_dir_is_noop(tmp_path: Path) -> None:
    base = tmp_path / "nope"
    assert prune_scraper_artifacts(base, max_age_days=1)["local_removed"] == 0
