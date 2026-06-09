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
        "tests/e2e/journeys/test_dev_env_journey.py",
        "-q",
        "--tb=short",
    ]
    for attempt in (1, 2):
        print(f"dev-env soak pass {attempt}/2", flush=True)
        proc = subprocess.run(cmd, cwd=root)
        if proc.returncode != 0:
            return proc.returncode
    print("dev-env weekly soak OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
