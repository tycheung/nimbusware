#!/usr/bin/env python3
"""Operational wrapper for the Nimbusware agent run-dispatch worker.

Provides copy-paste entrypoint with sane defaults for queue-drain testing:
- heartbeat file output
- finite idle loop exit for smoke checks
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run Nimbusware agent dispatch worker with ops defaults"
    )
    p.add_argument("--max-tasks", type=int, default=None)
    p.add_argument("--max-idle-loops", type=int, default=50)
    p.add_argument("--idle-sleep-seconds", type=float, default=0.1)
    p.add_argument("--heartbeat-path", type=str, default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = _args(argv)
    repo = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    hb = ns.heartbeat_path or str(repo / ".cache" / "run_dispatch_worker_heartbeat.json")
    cmd = [
        sys.executable,
        "-m",
        "nimbusware_orchestrator.run_worker",
        "--max-idle-loops",
        str(ns.max_idle_loops),
        "--idle-sleep-seconds",
        str(max(float(ns.idle_sleep_seconds), 0.0)),
        "--heartbeat-path",
        hb,
    ]
    if ns.max_tasks is not None:
        cmd.extend(["--max-tasks", str(ns.max_tasks)])
    proc = subprocess.run(cmd, cwd=repo, check=False)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
