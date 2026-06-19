#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_first_publish_gates_quick() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "publish" / "first_publish_gates.py"), "--quick"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
