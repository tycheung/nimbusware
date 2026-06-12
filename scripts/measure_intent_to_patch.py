#!/usr/bin/env python3
"""Measure patch run.created → first slice.applied median on tiny_python_app fixture."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "packages") not in sys.path:
    sys.path.insert(0, str(_REPO / "packages"))
if str(_REPO / "tests") not in sys.path:
    sys.path.insert(0, str(_REPO / "tests"))

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault("NIMBUSWARE_SLICE_IMPLEMENT", "stub")
os.environ.setdefault("NIMBUSWARE_SLICE_AUTO_ADVANCE", "0")
os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(_REPO))


def _run_once(tmp: Path) -> float | None:
    from fastapi.testclient import TestClient

    from e2e.harness.journey import JourneyClient
    from e2e.harness.workspace import copy_fixture_repo
    from nimbusware_api.app import app

    ws = copy_fixture_repo("tiny_python_app", tmp / "ws")
    (ws / "packages/nimbusware_orchestrator").mkdir(parents=True, exist_ok=True)
    (ws / "packages/nimbusware_orchestrator/micro_slice.py").write_text("# stub\n", encoding="utf-8")
    (ws / "packages/nimbusware_orchestrator/slice_gate.py").write_text("# stub\n", encoding="utf-8")

    t0 = time.perf_counter()
    with TestClient(app) as client:
        jc = JourneyClient(client=client)
        jc.attach_project(ws)
        run_resp = jc.client.post(
            "/v1/runs",
            json={
                "workflow_profile": "patch",
                "project_id": jc.project_id,
                "requirements": {"business_prompt": "Fix calculator test"},
                "work_type": "patch",
                "work_type_source": "classifier",
            },
        )
        if run_resp.status_code != 200:
            return None
        jc.run_id = str(run_resp.json().get("run_id") or "")
        if not jc.run_id:
            return None
        pending = jc.get_pending()
        if pending.get("plan_approved") is False:
            jc.approve_plan()
        prep = jc.prepare_slice()
        if prep.get("status") != "awaiting_approval":
            return None
        slice_id = prep["pending"]["slice_id"]
        applied = jc.apply_slice(slice_id)
        if applied.get("status") != "applied":
            return None
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return elapsed_ms


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path", default="")
    parser.add_argument("--runs", type=int, default=1)
    args = parser.parse_args(argv)
    tmp = _REPO / ".cache" / "intent_to_patch_measure"
    if tmp.is_dir():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    samples: list[float] = []
    for _ in range(max(1, args.runs)):
        delta = _run_once(tmp)
        if delta is not None:
            samples.append(delta)
    ordered = sorted(samples)
    median = None
    if ordered:
        mid = len(ordered) // 2
        median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0
    body = {
        "ok": bool(samples),
        "sample_size": len(samples),
        "median_ms": median,
        "target_median_ms": 180_000,
        "meets_target": median is not None and median <= 180_000,
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fixture": "tests/fixtures/repos/tiny_python_app",
    }
    if args.json_path:
        out = Path(args.json_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(body, indent=2))
    return 0 if body["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
