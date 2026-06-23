#!/usr/bin/env python3
"""CI gate: fail when prune_verbose_comments would modify tracked source."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ci" / "prune_verbose_comments.py"), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        print(out, file=sys.stderr)
        return proc.returncode
    for line in out.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("pruned "):
            continue
        print(
            "Redundant comments detected — run: "
            "poetry run python scripts/ci/prune_verbose_comments.py",
            file=sys.stderr,
        )
        print(stripped, file=sys.stderr)
        return 1
    print("prune comments gate: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
