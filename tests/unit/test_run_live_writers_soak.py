from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve())
SCRIPT = ROOT / "scripts" / "ops" / "run_live_writers_soak.py"
OUT = ROOT / "benchmarks" / "latest_live_writers_soak.json"


def _minimal_soak_env() -> dict[str, str]:
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


def test_run_live_writers_soak_writes_benchmark() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        env=_minimal_soak_env(),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()
    body = json.loads(OUT.read_text(encoding="utf-8"))
    assert body["live_writer_flags_ok"] is True
    assert body["writer_flags"]["refactor_stub_only"] is False
    assert body["writer_flags"]["integration_adapter_writer_stub_only"] is False
    assert body.get("published_at")
