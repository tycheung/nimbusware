#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(name: str, cmd: list[str]) -> int:
    print(f"=== {name} ===", flush=True)
    return subprocess.run(cmd, cwd=ROOT).returncode


def main() -> int:
    code = _run(
        "standards architecture+complexity",
        [sys.executable, str(ROOT / "scripts" / "ci" / "run_all_streams.py"), "--profile", "nimbusware-core"],
    )
    if code != 0:
        return code
    print("fast gates: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
