"""CLI tests for ``scripts/prune_scraper_artifacts.py``."""

from __future__ import annotations
from nimbusware_env import find_repo_root

import json
import os
import subprocess
import time
from pathlib import Path

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def _run_prune_script(
    repo_root: Path,
    *,
    extra_args: list[str],
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "NIMBUSWARE_REPO_ROOT": str(repo_root)}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [
            "poetry",
            "run",
            "python",
            str(ROOT / "scripts" / "prune_scraper_artifacts.py"),
            "--max-age-days",
            "7",
            *extra_args,
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_prune_scraper_artifacts_help_lists_json_summary() -> None:
    proc = subprocess.run(
        [
            "poetry",
            "run",
            "python",
            str(ROOT / "scripts" / "prune_scraper_artifacts.py"),
            "--help",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--json-summary" in proc.stdout
    assert "max_age_days" in proc.stdout

    assert "--include-pattern" in proc.stdout
    assert "--exclude-pattern" in proc.stdout


def test_prune_scraper_artifacts_json_summary_second_line(tmp_path: Path) -> None:
    base = tmp_path / ".cache" / "hermes_scraper"
    run_dir = base / "00000000-0000-4000-8000-000000000001"
    run_dir.mkdir(parents=True)
    stale = run_dir / "url00_deadbeef.bin"
    stale.write_bytes(b"x")
    old = time.time() - 10 * 86400
    os.utime(stale, (old, old))

    proc = _run_prune_script(tmp_path, extra_args=["--json-summary"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln]
    assert len(lines) == 2
    assert lines[0].startswith("pruned ")
    summary = json.loads(lines[1])
    assert summary["schema_version"] == 1
    assert summary["pruned"] == 1
    assert summary["dry_run"] is False
    assert summary["max_age_days"] == 7
    assert summary["base"] == str(base.resolve())
    assert summary["include_pattern_count"] == 0
    assert summary["exclude_pattern_count"] == 0
    assert summary["retention_execution_mode"] == "local_only"
    assert summary["retention_stale_file_count"] == 1
    assert summary["retention_stale_bytes"] == 1
    assert summary["retention_alert_level"] == "stale_present"
    assert summary["retention_lifecycle_state"] == "pruned"
    assert summary["object_store_attempted"] == 0
    assert summary["object_store_removed"] == 0
    assert summary["object_store_failed"] == 0
    assert summary["object_store_last_error"] is None


def test_prune_scraper_artifacts_json_summary_with_dry_run(tmp_path: Path) -> None:
    base = tmp_path / ".cache" / "hermes_scraper"
    run_dir = base / "00000000-0000-4000-8000-000000000001"
    run_dir.mkdir(parents=True)
    stale = run_dir / "url00_deadbeef.bin"
    stale.write_bytes(b"x")
    old = time.time() - 10 * 86400
    os.utime(stale, (old, old))

    proc = _run_prune_script(tmp_path, extra_args=["--dry-run", "--json-summary"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln]
    assert len(lines) == 2
    assert lines[0].startswith("dry-run:")
    summary = json.loads(lines[1])
    assert summary["schema_version"] == 1
    assert summary["pruned"] == 1
    assert summary["dry_run"] is True
    assert summary["max_age_days"] == 7
    assert summary["include_pattern_count"] == 0
    assert summary["exclude_pattern_count"] == 0
    assert summary["retention_stale_file_count"] == 1
    assert summary["retention_stale_bytes"] == 1
    assert summary["retention_alert_level"] == "stale_present"
    assert summary["retention_lifecycle_state"] == "dry_run_preview"
    assert stale.is_file()


def test_prune_json_summary_includes_last_object_store_error(tmp_path: Path) -> None:
    base = tmp_path / ".cache" / "hermes_scraper"
    run_dir = base / "00000000-0000-4000-8000-000000000001"
    run_dir.mkdir(parents=True)
    stale = run_dir / "url00_deadbeef.bin"
    stale.write_bytes(b"x")
    old = time.time() - 10 * 86400
    os.utime(stale, (old, old))
    proc = _run_prune_script(
        tmp_path,
        extra_args=["--json-summary"],
        extra_env={
            "HERMES_SCRAPER_ARTIFACT_OBJECT_STORE_PRUNE": "1",
            "HERMES_SCRAPER_ARTIFACT_OBJECT_STORE_URL": "https://s3.example.com",
            "HERMES_SCRAPER_ARTIFACT_OBJECT_STORE_BUCKET": "b",
            "HERMES_SCRAPER_ARTIFACT_OBJECT_STORE_TIMEOUT_SECONDS": "1",
            "HERMES_SCRAPER_ARTIFACT_OBJECT_STORE_DELETE_MAX_ATTEMPTS": "1",
        },
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    summary = json.loads([ln for ln in proc.stdout.strip().splitlines() if ln][1])
    assert summary["retention_execution_mode"] == "local_with_object_store_mirror"
    assert summary["object_store_attempted"] == 1
    assert summary["object_store_failed"] == 1
    assert summary["retention_lifecycle_state"] == "mirror_degraded"
    assert isinstance(summary["object_store_last_error"], str)


def test_prune_include_pattern_filters_and_summary_echoes_patterns(tmp_path: Path) -> None:
    """fo125: ``--include-pattern '*.bin'`` only deletes ``.bin``; summary echoes the list."""
    base = tmp_path / ".cache" / "hermes_scraper"
    run_dir = base / "00000000-0000-4000-8000-000000000001"
    run_dir.mkdir(parents=True)
    stale_bin = run_dir / "url00_deadbeef.bin"
    stale_txt = run_dir / "meta.txt"
    for p in (stale_bin, stale_txt):
        p.write_bytes(b"x")
        old = time.time() - 10 * 86400
        os.utime(p, (old, old))

    proc = _run_prune_script(
        tmp_path,
        extra_args=["--include-pattern", "*.bin", "--json-summary"],
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln]
    assert len(lines) == 2
    summary = json.loads(lines[1])
    assert summary["schema_version"] == 1
    assert summary["pruned"] == 1
    assert summary["include_patterns"] == ["*.bin"]
    assert summary["exclude_patterns"] is None
    assert summary["include_pattern_count"] == 1
    assert summary["exclude_pattern_count"] == 0
    # On-disk truth: only the .bin file was removed
    assert not stale_bin.is_file()
    assert stale_txt.is_file()


def test_prune_exclude_pattern_preserves_matches_and_summary_echoes_patterns(
    tmp_path: Path,
) -> None:
    """fo125: ``--exclude-pattern '*.keep'`` preserves matches; summary lists the pattern."""
    base = tmp_path / ".cache" / "hermes_scraper"
    run_dir = base / "00000000-0000-4000-8000-000000000001"
    run_dir.mkdir(parents=True)
    stale_bin = run_dir / "url00_deadbeef.bin"
    stale_keep = run_dir / "pinned.keep"
    for p in (stale_bin, stale_keep):
        p.write_bytes(b"x")
        old = time.time() - 10 * 86400
        os.utime(p, (old, old))

    proc = _run_prune_script(
        tmp_path,
        extra_args=["--exclude-pattern", "*.keep", "--json-summary"],
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln]
    assert len(lines) == 2
    summary = json.loads(lines[1])
    assert summary["schema_version"] == 1
    assert summary["pruned"] == 1
    assert summary["include_patterns"] is None
    assert summary["exclude_patterns"] == ["*.keep"]
    assert summary["include_pattern_count"] == 0
    assert summary["exclude_pattern_count"] == 1
    assert not stale_bin.is_file()
    assert stale_keep.is_file()


def test_prune_env_include_pattern_defaults(tmp_path: Path) -> None:
    """Comma-separated ``HERMES_PRUNE_INCLUDE_PATTERN`` when no CLI include flags."""
    base = tmp_path / ".cache" / "hermes_scraper"
    run_dir = base / "00000000-0000-4000-8000-000000000001"
    run_dir.mkdir(parents=True)
    stale_bin = run_dir / "url00_deadbeef.bin"
    stale_txt = run_dir / "meta.txt"
    for p in (stale_bin, stale_txt):
        p.write_bytes(b"x")
        old = time.time() - 10 * 86400
        os.utime(p, (old, old))

    proc = _run_prune_script(
        tmp_path,
        extra_args=["--json-summary"],
        extra_env={"HERMES_PRUNE_INCLUDE_PATTERN": "*.bin"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    summary = json.loads([ln for ln in proc.stdout.strip().splitlines() if ln][1])
    assert summary["schema_version"] == 1
    assert summary["include_patterns"] == ["*.bin"]
    assert summary["pruned"] == 1
    assert summary["include_pattern_count"] == 1
    assert summary["exclude_pattern_count"] == 0
    assert not stale_bin.is_file()
    assert stale_txt.is_file()


def test_prune_cli_include_overrides_env(tmp_path: Path) -> None:
    base = tmp_path / ".cache" / "hermes_scraper"
    run_dir = base / "00000000-0000-4000-8000-000000000001"
    run_dir.mkdir(parents=True)
    stale_bin = run_dir / "url00_deadbeef.bin"
    stale_txt = run_dir / "meta.txt"
    for p in (stale_bin, stale_txt):
        p.write_bytes(b"x")
        old = time.time() - 10 * 86400
        os.utime(p, (old, old))

    proc = _run_prune_script(
        tmp_path,
        extra_args=["--include-pattern", "*.txt", "--json-summary"],
        extra_env={"HERMES_PRUNE_INCLUDE_PATTERN": "*.bin"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    summary = json.loads([ln for ln in proc.stdout.strip().splitlines() if ln][1])
    assert summary["schema_version"] == 1
    assert summary["include_patterns"] == ["*.txt"]
    assert summary["pruned"] == 1
    assert summary["include_pattern_count"] == 1
    assert summary["exclude_pattern_count"] == 0
    assert stale_bin.is_file()
    assert not stale_txt.is_file()
