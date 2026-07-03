from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve())
SCRIPT = ROOT / "scripts" / "ops" / "run_fo2172_live_journey_soak.py"
GATE = ROOT / "scripts" / "ci" / "run_fo2172_live_ci_gate.py"
OUT = ROOT / "benchmarks" / "latest_fo2172_live_journey.json"


def _minimal_env() -> dict[str, str]:
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
    env["NIMBUSWARE_SKIP_PREFLIGHT"] = "1"
    env["NIMBUSWARE_REPO_ROOT"] = str(ROOT)
    return env


def test_run_fo2172_live_journey_soak_writes_opt_in_snapshot() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env=_minimal_env(),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()
    body = json.loads(OUT.read_text(encoding="utf-8"))
    assert body["ok"] is True
    assert body["skipped"] is True
    assert body.get("published_at")


def test_fo2172_live_ci_gate_snapshot_only() -> None:
    proc = subprocess.run(
        [sys.executable, str(GATE), "--snapshot-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=_minimal_env(),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
