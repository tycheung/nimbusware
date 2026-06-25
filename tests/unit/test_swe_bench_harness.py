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


def _minimal_benchmark_env(**extra: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for key in (
        "PATH",
        "SYSTEMROOT",
        "PATHEXT",
        "WINDIR",
        "HOME",
        "USERPROFILE",
        "TEMP",
        "TMP",
    ):
        value = os.environ.get(key)
        if value:
            env[key] = value
    env.update(
        {
            "NIMBUSWARE_SKIP_PREFLIGHT": "1",
            "NIMBUSWARE_REPO_ROOT": str(ROOT),
            "NIMBUSWARE_VERIFY_DISPATCH_FANOUT": "0",
            "NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS": "1",
            "NIMBUSWARE_ENABLE_TEST_WRITER_CRITIQUE": "0",
            **extra,
        }
    )
    return env


def _run_harness_json(*args: str, **env_extra: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        env=_minimal_benchmark_env(**env_extra),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    body = json.loads(proc.stdout)
    assert isinstance(body, dict)
    return body


def test_swe_bench_dry_run_json_ok() -> None:
    summary = _run_harness_json("--dry-run", "--json")
    assert summary["ok"] is True
    assert summary["workflow_profile"] == "micro_slice"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["fixture_subdir"] == "repo"


def test_swe_bench_run_json_scores() -> None:
    summary = _run_harness_json("--run", "--json", NIMBUSWARE_MICRO_SLICE_COUNT="1")
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
        env=_minimal_benchmark_env(NIMBUSWARE_MICRO_SLICE_COUNT="1"),
    )
    assert proc.returncode != 0, proc.stdout
    summary = json.loads(proc.stdout)
    assert summary["ok"] is False
    assert "min_pass_rate_fail" in summary.get("checks", [])


def test_swe_bench_writes_json_snapshot() -> None:
    summary = _run_harness_json(
        "--run",
        "--json",
        NIMBUSWARE_MICRO_SLICE_COUNT="1",
        NIMBUSWARE_SWE_BENCH_WRITE_JSON="1",
        NIMBUSWARE_SWE_BENCH_MANIFEST=str(MANIFEST),
    )
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
