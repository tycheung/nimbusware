#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _redis_reachable(url: str) -> bool:
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


def _redis_fleet_urls() -> list[str]:
    fleet = os.environ.get("NIMBUSWARE_REDIS_FLEET_URLS", "").strip()
    if fleet:
        urls = [part.strip() for part in fleet.split(",") if part.strip()]
        if urls:
            return urls
    default = os.environ.get("NIMBUSWARE_REDIS_URL", "redis://127.0.0.1:6379/0").strip()
    return [default]


def campaign_soak_check(*, repo_root: Path | None = None) -> dict[str, Any]:
    repo = repo_root or Path(__file__).resolve().parents[2]
    urls = _redis_fleet_urls()
    nodes: list[dict[str, Any]] = []
    for url in urls:
        nodes.append({"redis_url": url, "reachable": _redis_reachable(url)})
    dispatch = os.environ.get("NIMBUSWARE_RUN_DISPATCH", "").strip().lower()
    edition = os.environ.get("NIMBUSWARE_EDITION", "individual").strip().lower()
    worker_script = repo / "scripts" / "ops" / "run_dispatch_worker.py"
    ready = (
        bool(urls)
        and all(node["reachable"] for node in nodes)
        and dispatch == "redis"
        and edition == "enterprise"
        and worker_script.is_file()
    )
    return {
        "redis_urls": urls,
        "nodes": nodes,
        "run_dispatch": dispatch or None,
        "edition": edition,
        "worker_script": str(worker_script),
        "ready": ready,
        "runbook": "docs/deploy/campaign-soak-runbook.md",
    }


def main() -> int:
    summary = campaign_soak_check()
    print(json.dumps(summary, sort_keys=True))
    if not summary["nodes"]:
        print("Skip: set NIMBUSWARE_REDIS_FLEET_URLS or NIMBUSWARE_REDIS_URL")
        return 0
    if not all(node["reachable"] for node in summary["nodes"]):
        print("Fail: one or more Redis brokers unreachable")
        return 1
    if not summary["ready"]:
        print(
            "Warn: Redis reachable but soak not fully configured "
            "(need NIMBUSWARE_RUN_DISPATCH=redis, NIMBUSWARE_EDITION=enterprise)"
        )
        return 0
    print("OK: campaign soak prerequisites satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
