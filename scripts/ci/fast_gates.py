#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(name: str, cmd: list[str]) -> int:
    print(f"=== {name} ===", flush=True)
    code = subprocess.run(cmd, cwd=ROOT).returncode
    if code != 0:
        print(f"fast gates: failed at {name}", flush=True)
    return code


def main() -> int:
    py = sys.executable
    steps: list[tuple[str, list[str]]] = [
        (
            "ruff check",
            [py, "-m", "ruff", "check", "packages", "tests"],
        ),
        (
            "composite test size",
            [py, str(ROOT / "scripts" / "ci" / "run_composite_test_size_gate.py")],
        ),
        (
            "standards streams (core profile)",
            [py, str(ROOT / "scripts" / "ci" / "run_all_streams.py"), "--profile", "nimbusware-core"],
        ),
    ]
    for name, cmd in steps:
        if _run(name, cmd) != 0:
            return 1
    print("fast gates: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
