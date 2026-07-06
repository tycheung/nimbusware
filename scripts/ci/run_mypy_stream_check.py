#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    proc = subprocess.run(
        ["poetry", "run", "python", "scripts/ci/mypy_ci_targets.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode
    targets = proc.stdout.split()
    if not targets:
        print("mypy stream: no targets", file=sys.stderr)
        return 1
    mypy = subprocess.run(["poetry", "run", "mypy", *targets], cwd=ROOT)
    return mypy.returncode


if __name__ == "__main__":
    raise SystemExit(main())
