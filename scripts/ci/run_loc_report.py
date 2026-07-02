#!/usr/bin/env python3
"""Print LOC summary JSON for CI logs and PR visibility."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ci" / "count_loc.py"), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr or proc.stdout)
        return proc.returncode
    payload = json.loads(proc.stdout)
    source = payload.get("source") or []
    packages_py = sum(
        int(row.get("non_blank") or 0)
        for row in source
        if str(row.get("path", "")).startswith("packages/") and str(row.get("path", "")).endswith(".py")
    )
    tests_py = sum(
        int(row.get("non_blank") or 0)
        for row in source
        if str(row.get("path", "")).startswith("tests/") and str(row.get("path", "")).endswith(".py")
    )
    summary = {
        "packages_python_non_blank_lines": packages_py,
        "tests_python_non_blank_lines": tests_py,
        "totals": payload.get("totals") or {},
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
