from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])
MANIFEST = ROOT / "tests" / "fixtures" / "swe_bench" / "manifest.json"
SCRIPT = ROOT / "scripts" / "benchmarks" / "swe_bench_harness.py"


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
            "NIMBUSWARE_SKIP_PREFLIGHT": "1",
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
            "NIMBUSWARE_SKIP_PREFLIGHT": "1",
            "NIMBUSWARE_REPO_ROOT": str(ROOT),
            "NIMBUSWARE_MICRO_SLICE_COUNT": "1",
        },
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    summary = json.loads(proc.stdout)
    assert summary["mode"] == "run"
    assert summary["slices_total"] >= 1
    assert "pass_rate" in summary
    assert summary["run_id"]
    assert summary["pass_rate"] == 1.0


def test_swe_bench_min_pass_rate_failure(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (repo / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )
    bad_manifest = tmp_path / "manifest.json"
    bad_manifest.write_text(
        json.dumps(
            {
                "workflow_profile": "micro_slice",
                "fixture_subdir": "repo",
                "min_pass_rate": 2.0,
                "fixture_target_paths": ["calc.py"],
                "benchmark_env": {
                    "NIMBUSWARE_USE_LLM": "0",
                    "NIMBUSWARE_SLICE_IMPLEMENT": "stub",
                    "NIMBUSWARE_SLICE_P3_EVIDENCE": "0",
                },
            },
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--run", "--json", "--manifest", str(bad_manifest)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        env={
            **os.environ,
            "NIMBUSWARE_SKIP_PREFLIGHT": "1",
            "NIMBUSWARE_REPO_ROOT": str(ROOT),
            "NIMBUSWARE_MICRO_SLICE_COUNT": "1",
        },
    )
    assert proc.returncode != 0, proc.stdout
    summary = json.loads(proc.stdout)
    assert summary["ok"] is False
    assert "min_pass_rate_fail" in summary.get("checks", [])


def test_swe_bench_writes_json_snapshot() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--run", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        env={
            **os.environ,
            "NIMBUSWARE_SKIP_PREFLIGHT": "1",
            "NIMBUSWARE_REPO_ROOT": str(ROOT),
            "NIMBUSWARE_MICRO_SLICE_COUNT": "1",
            "NIMBUSWARE_SWE_BENCH_WRITE_JSON": "1",
            "NIMBUSWARE_SWE_BENCH_MANIFEST": str(MANIFEST),
        },
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    # Harness writes under repo benchmarks/; verify flag recorded in summary.
    summary = json.loads(proc.stdout)
    assert any(str(c).startswith("wrote=") for c in summary.get("checks", []))
    swe_path = ROOT / "benchmarks" / "latest_swe_bench.json"
    assert swe_path.is_file()
    body = json.loads(swe_path.read_text(encoding="utf-8"))
    assert body["run_id"]
    assert body["manifest_path"].startswith("tests/fixtures/swe_bench/")
    assert "published_at" in body
    critic_path = ROOT / "benchmarks" / "latest_critic_reliability.json"
    assert critic_path.is_file()
    critic = json.loads(critic_path.read_text(encoding="utf-8"))
    assert critic.get("source") == "swe_bench_harness"
    assert critic.get("source_run_id") == body["run_id"]
