#!/usr/bin/env python3
"""Redis fleet stack soak for scheduled CI (see scripts/e2e_redis_fleet_soak_runbook.md)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def redis_reachable(url: str) -> bool:
    try:
        import redis
    except ImportError:
        return False
    try:
        client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=2.0)
        client.ping()
        return True
    except Exception:
        return False


def run_redis_fleet_soak(*, repo_root: Path | None = None) -> dict[str, Any]:
    repo = repo_root or Path(__file__).resolve().parents[1]
    url = os.environ.get("NIMBUSWARE_REDIS_URL", "redis://127.0.0.1:6379/0").strip()
    summary: dict[str, Any] = {"redis_url": url, "skipped": False, "passed": False}
    if not redis_reachable(url):
        summary["skipped"] = True
        summary["reason"] = "redis_unreachable"
        return summary
    env = os.environ.copy()
    env.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
    env.setdefault("NIMBUSWARE_REPO_ROOT", str(repo))
    env["NIMBUSWARE_REDIS_URL"] = url
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/integration/test_redis_dispatch_worker_stack.py",
        "-m",
        "integration and e2e_stack",
        "-q",
    ]
    proc = subprocess.run(cmd, cwd=repo, env=env, check=False)
    summary["exit_code"] = proc.returncode
    summary["passed"] = proc.returncode == 0
    return summary


def main() -> int:
    summary = run_redis_fleet_soak()
    print(json.dumps(summary, sort_keys=True))
    if summary.get("skipped"):
        print("Skip: Redis not reachable (set NIMBUSWARE_REDIS_URL for fleet soak)")
        return 0
    return 0 if summary.get("passed") else int(summary.get("exit_code") or 1)


if __name__ == "__main__":
    raise SystemExit(main())
