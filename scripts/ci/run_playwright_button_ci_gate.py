#!/usr/bin/env python3
"""CI gate: Playwright button inventory freshness + click wiring contract."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    audit = ROOT / "scripts" / "ci" / "audit_playwright_button_coverage.py"
    proc = subprocess.run(
        [sys.executable, str(audit), "--check"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/web/test_playwright_button_coverage.py", "-q"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("playwright button gate ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
