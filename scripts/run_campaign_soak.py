#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _journey_tests(repo_root: Path) -> list[str]:
    default = (
        "tests/e2e/journeys/test_tiny_api_campaign_dispatch_journey.py,"
        "tests/e2e/journeys/test_campaign_dispatch_worker_journey.py"
    )
    raw = os.environ.get("NIMBUSWARE_CAMPAIGN_SOAK_JOURNEYS", default).strip()
    paths = [part.strip() for part in raw.split(",") if part.strip()]
    return [str((repo_root / rel).as_posix()) for rel in paths if (repo_root / rel).is_file()]


def run_campaign_soak(*, repo_root: Path | None = None) -> dict[str, Any]:
    repo = repo_root or Path(__file__).resolve().parents[1]
    passes = max(1, int(os.environ.get("NIMBUSWARE_CAMPAIGN_SOAK_PASSES", "2") or 2))
    journeys = _journey_tests(repo)
    nodes: list[dict[str, Any]] = []
    passed = True
    for journey in journeys:
        node: dict[str, Any] = {"journey": journey, "passes": []}
        for attempt in range(1, passes + 1):
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", journey, "-q", "--tb=short"],
                cwd=repo,
                env={**os.environ, "NIMBUSWARE_SKIP_PREFLIGHT": "1"},
            )
            entry = {"attempt": attempt, "exit_code": proc.returncode}
            node["passes"].append(entry)
            if proc.returncode != 0:
                passed = False
                break
        nodes.append(node)
        if not passed:
            break
    return {
        "journeys": journeys,
        "passes_per_journey": passes,
        "nodes": nodes,
        "passed": passed and bool(journeys),
        "skipped": not journeys,
    }


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from run_campaign_soak_check import campaign_soak_check

    preflight = campaign_soak_check(repo_root=repo)
    print(json.dumps({"preflight": preflight}, sort_keys=True))
    if preflight.get("nodes") and not all(n.get("reachable") for n in preflight["nodes"]):
        print("Skip: Redis unreachable for campaign soak")
        return 0
    summary = run_campaign_soak()
    print(json.dumps(summary, sort_keys=True))
    if summary.get("skipped"):
        print("Skip: no campaign soak journey tests found")
        return 0
    if summary.get("passed"):
        print("OK: campaign soak passed")
        return 0
    print("Fail: campaign soak journey failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
