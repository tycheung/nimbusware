#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ci" / "trim_redundant_docstrings.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        print(out, file=sys.stderr)
        print(
            "Run: poetry run python scripts/ci/trim_redundant_docstrings.py",
            file=sys.stderr,
        )
        return proc.returncode
    print("trim docstrings gate: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
