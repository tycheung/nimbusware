#!/usr/bin/env python3
"""Redis fleet stack soak for scheduled CI (see scripts/runbooks/e2e_redis_fleet_soak_runbook.md)."""

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


def redis_fleet_urls() -> list[str]:
    fleet = os.environ.get("NIMBUSWARE_REDIS_FLEET_URLS", "").strip()
    if fleet:
        urls = [part.strip() for part in fleet.split(",") if part.strip()]
        if urls:
            return urls
    default = os.environ.get("NIMBUSWARE_REDIS_URL", "redis://127.0.0.1:6379/0").strip()
    return [default]


def run_redis_fleet_soak_for_url(
    url: str,
    *,
    repo_root: Path,
) -> dict[str, Any]:
    node: dict[str, Any] = {"redis_url": url, "skipped": False, "passed": False}
    if not redis_reachable(url):
        node["skipped"] = True
        node["reason"] = "redis_unreachable"
        return node
    env = os.environ.copy()
    env.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
    env.setdefault("NIMBUSWARE_REPO_ROOT", str(repo_root))
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
    proc = subprocess.run(cmd, cwd=repo_root, env=env, check=False)
    node["exit_code"] = proc.returncode
    node["passed"] = proc.returncode == 0
    return node


def run_redis_fleet_soak(*, repo_root: Path | None = None) -> dict[str, Any]:
    repo = repo_root or Path(__file__).resolve().parents[2]
    urls = redis_fleet_urls()
    nodes = [run_redis_fleet_soak_for_url(url, repo_root=repo) for url in urls]
    skipped = all(node.get("skipped") for node in nodes)
    passed = bool(nodes) and all(node.get("passed") for node in nodes if not node.get("skipped"))
    if skipped:
        return {
            "redis_urls": urls,
            "nodes": nodes,
            "skipped": True,
            "reason": "redis_unreachable",
            "passed": False,
        }
    return {
        "redis_urls": urls,
        "nodes": nodes,
        "skipped": False,
        "passed": passed,
        "node_count": len(nodes),
    }


def main() -> int:
    summary = run_redis_fleet_soak()
    print(json.dumps(summary, sort_keys=True))
    if summary.get("skipped"):
        print("Skip: Redis not reachable (set NIMBUSWARE_REDIS_URL for fleet soak)")
        return 0
    return 0 if summary.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
