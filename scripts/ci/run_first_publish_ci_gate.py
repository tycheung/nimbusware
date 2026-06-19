#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "publish" / "first_publish_gates.py"), "--quick"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("first publish quick gate OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
