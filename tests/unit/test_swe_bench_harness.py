"""SWE-bench harness dry-run (no network)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])
MANIFEST = ROOT / "tests" / "fixtures" / "swe_bench" / "manifest.json"
SCRIPT = ROOT / "scripts" / "swe_bench_harness.py"


def test_swe_bench_dry_run_json_ok() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env={
            **os.environ,
            "HERMES_SKIP_PREFLIGHT": "1",
            "NIMBUSWARE_REPO_ROOT": str(ROOT),
        },
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    summary = json.loads(proc.stdout)
    assert summary["ok"] is True
    assert summary["workflow_profile"] == "micro_slice"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["fixture_subdir"] == "repo"


def test_swe_bench_run_json_scores() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--run", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        env={
            **os.environ,
            "HERMES_SKIP_PREFLIGHT": "1",
            "NIMBUSWARE_REPO_ROOT": str(ROOT),
            "HERMES_MICRO_SLICE_COUNT": "1",
        },
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    summary = json.loads(proc.stdout)
    assert summary["mode"] == "run"
    assert summary["slices_total"] >= 1
    assert "pass_rate" in summary
    assert summary["run_id"]
