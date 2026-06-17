from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve())
SCRIPT = ROOT / "scripts" / "ops" / "run_live_writers_soak.py"
OUT = ROOT / "benchmarks" / "latest_live_writers_soak.json"


def test_run_live_writers_soak_writes_benchmark() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()
    body = json.loads(OUT.read_text(encoding="utf-8"))
    assert body["live_writer_flags_ok"] is True
    assert body["writer_flags"]["refactor_stub_only"] is False
    assert body["writer_flags"]["integration_adapter_writer_stub_only"] is False
    assert body.get("published_at")
