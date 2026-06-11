#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    env = {
        **os.environ,
        "NIMBUSWARE_SKIP_PREFLIGHT": "1",
        "NIMBUSWARE_REPO_ROOT": str(_ROOT),
        "NIMBUSWARE_MICRO_SLICE_COUNT": "1",
        "NIMBUSWARE_SWE_BENCH_WRITE_JSON": "1",
    }
    proc = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "swe_bench_harness.py"), "--run", "--json"],
        cwd=_ROOT,
        env=env,
        check=False,
    )
    out = _ROOT / "benchmarks" / "latest_swe_bench.json"
    if out.is_file():
        print(f"Wrote {out.relative_to(_ROOT)}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
