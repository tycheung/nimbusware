#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/test_publish_bootstrap_workflow.py",
        "-q",
        "--tb=short",
    ]
    proc = subprocess.run(cmd, cwd=root)
    if proc.returncode != 0:
        return proc.returncode
    print("publish bootstrap workflow CI gate OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
