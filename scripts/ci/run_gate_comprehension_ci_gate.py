#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEASURE = ROOT / "scripts" / "benchmarks" / "measure_gate_comprehension.py"


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(MEASURE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        return proc.returncode
    print("gate comprehension CI gate OK (fo2043)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
