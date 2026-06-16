from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def _seed_stale_artifact(repo_root: Path) -> Path:
    base = repo_root / ".cache" / "nimbusware_scraper"
    run_dir = base / "00000000-0000-4000-8000-000000000001"
    run_dir.mkdir(parents=True)
    stale = run_dir / "url00_deadbeef.bin"
    stale.write_bytes(b"x")
    old = time.time() - 10 * 86400
    os.utime(stale, (old, old))
    return stale


def _run_prune_script(
    repo_root: Path,
    *,
    extra_args: list[str],
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "NIMBUSWARE_REPO_ROOT": str(repo_root)}
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [
            "poetry",
            "run",
            "python",
            str(ROOT / "scripts" / "prune_scraper_artifacts.py"),
            "--max-age-days",
            "7",
            "--dry-run",
            *extra_args,
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _read_status(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


# Axis 1: --summary-path alone writes JSON with wrote_at


def test_summary_path_flag_writes_state_file(tmp_path: Path) -> None:
    _seed_stale_artifact(tmp_path)
    status_path = tmp_path / "state" / "prune_status.json"
    proc = _run_prune_script(tmp_path, extra_args=["--summary-path", str(status_path)])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert status_path.is_file()
    payload = _read_status(status_path)
    # All fo125 keys + max_age_days + the new fo126 wrote_at field must be present.
    assert set(payload.keys()) == {
        "schema_version",
        "pruned",
        "base",
        "dry_run",
        "max_age_days",
        "include_patterns",
        "exclude_patterns",
        "include_pattern_count",
        "exclude_pattern_count",
        "wrote_at",
    }
    assert payload["schema_version"] == 1
    assert payload["pruned"] == 1
    assert payload["dry_run"] is True
    assert payload["max_age_days"] == 7
    assert payload["include_patterns"] is None
    assert payload["exclude_patterns"] is None
    assert payload["include_pattern_count"] == 0
    assert payload["exclude_pattern_count"] == 0
    # ``wrote_at`` must round-trip through ``fromisoformat``.
    parsed = datetime.fromisoformat(str(payload["wrote_at"]))
    assert parsed.tzinfo is not None, "wrote_at must be a tz-aware UTC ISO 8601 string"


# Axis 2: NIMBUSWARE_PRUNE_STATUS_PATH env writes the same file


def test_env_var_alone_writes_state_file(tmp_path: Path) -> None:
    _seed_stale_artifact(tmp_path)
    status_path = tmp_path / "state" / "prune_status.json"
    proc = _run_prune_script(
        tmp_path,
        extra_args=[],
        env_overrides={"NIMBUSWARE_PRUNE_STATUS_PATH": str(status_path)},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert status_path.is_file()
    payload = _read_status(status_path)
    assert payload["schema_version"] == 1
    assert payload["pruned"] == 1
    assert "wrote_at" in payload


# Axis 3: CLI flag wins over env when both are set


def test_cli_flag_overrides_env(tmp_path: Path) -> None:
    _seed_stale_artifact(tmp_path)
    env_path = tmp_path / "state" / "from_env.json"
    cli_path = tmp_path / "state" / "from_cli.json"
    proc = _run_prune_script(
        tmp_path,
        extra_args=["--summary-path", str(cli_path)],
        env_overrides={"NIMBUSWARE_PRUNE_STATUS_PATH": str(env_path)},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert cli_path.is_file(), "CLI --summary-path should win and create the file"
    assert not env_path.exists(), "Env-resolved path must NOT be written when --summary-path is set"


# Axis 4: Atomic write — .tmp sibling cleaned up after success


def test_atomic_write_leaves_no_tmp_sibling(tmp_path: Path) -> None:
    _seed_stale_artifact(tmp_path)
    status_path = tmp_path / "state" / "prune_status.json"
    proc = _run_prune_script(tmp_path, extra_args=["--summary-path", str(status_path)])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    tmp_sibling = status_path.with_suffix(status_path.suffix + ".tmp")
    assert status_path.is_file()
    assert not tmp_sibling.exists(), (
        f"Atomic write should clean up the .tmp sibling; found stray file at {tmp_sibling}"
    )


# Axis 5: State file content matches --json-summary stdout (minus wrote_at)


def test_state_file_matches_json_summary_stdout(tmp_path: Path) -> None:
    _seed_stale_artifact(tmp_path)
    status_path = tmp_path / "state" / "prune_status.json"
    proc = _run_prune_script(
        tmp_path,
        extra_args=[
            "--summary-path",
            str(status_path),
            "--json-summary",
            "--include-pattern",
            "*.bin",
        ],
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln]
    # human line + JSON summary line
    assert len(lines) == 2
    stdout_summary = json.loads(lines[1])
    file_payload = _read_status(status_path)
    # File payload is the stdout summary plus exactly one extra key: wrote_at.
    assert "wrote_at" in file_payload
    file_payload_without_ts = {k: v for k, v in file_payload.items() if k != "wrote_at"}
    assert file_payload_without_ts == stdout_summary
    assert stdout_summary["include_patterns"] == ["*.bin"]


def test_dual_flag_json_summary_omits_extended_retention_fields(tmp_path: Path) -> None:
    """When ``--summary-path`` is set, stdout JSON uses the slim base summary."""
    _seed_stale_artifact(tmp_path)
    status_path = tmp_path / "state" / "prune_status.json"
    proc = _run_prune_script(
        tmp_path,
        extra_args=["--summary-path", str(status_path), "--json-summary"],
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    stdout_summary = json.loads([ln for ln in proc.stdout.strip().splitlines() if ln][1])
    assert stdout_summary["schema_version"] == 1
    assert "retention_execution_mode" not in stdout_summary
    assert "object_store_attempted" not in stdout_summary


def test_standalone_json_summary_includes_extended_retention_fields(tmp_path: Path) -> None:
    """Standalone ``--json-summary`` keeps extended retention/object-store fields."""
    _seed_stale_artifact(tmp_path)
    proc = _run_prune_script(tmp_path, extra_args=["--json-summary"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    summary = json.loads([ln for ln in proc.stdout.strip().splitlines() if ln][1])
    assert summary["retention_execution_mode"] == "local_only"
    assert "object_store_attempted" in summary
