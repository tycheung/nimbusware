#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/test_bootstrap_wheel_build.py",
        "tests/unit/test_bootstrap_wheel_install.py",
        "tests/unit/test_consumer_bootstrap.py",
        "-q",
        "--tb=short",
    ]
    proc = subprocess.run(cmd, cwd=root)
    if proc.returncode != 0:
        return proc.returncode
    print("bootstrap CI gate OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
