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

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO / "packages") not in sys.path:
    sys.path.insert(0, str(_REPO / "packages"))
if str(_REPO / "tests") not in sys.path:
    sys.path.insert(0, str(_REPO / "tests"))

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault("NIMBUSWARE_SLICE_IMPLEMENT", "stub")
os.environ.setdefault("NIMBUSWARE_SLICE_AUTO_ADVANCE", "0")
os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(_REPO))


def _bind_inmemory_chat(client) -> None:
    from maker.chat_store import InMemoryChatStore

    client.app.state.chat_store = InMemoryChatStore()


def _prepare_workspace(tmp: Path) -> Path:
    from e2e.harness.workspace import copy_fixture_repo

    ws = copy_fixture_repo("tiny_python_app", tmp / "ws")
    (ws / "packages/orchestrator").mkdir(parents=True, exist_ok=True)
    (ws / "packages/orchestrator/micro_slice.py").write_text(
        "# stub\n", encoding="utf-8"
    )
    (ws / "packages/orchestrator/slice_gate.py").write_text("# stub\n", encoding="utf-8")
    return ws


def _complete_patch_slice(jc) -> bool:
    pending = jc.get_pending()
    if pending.get("plan_approved") is False:
        jc.approve_plan()
    prep = jc.prepare_slice()
    if prep.get("status") != "awaiting_approval":
        return False
    slice_id = prep["pending"]["slice_id"]
    applied = jc.apply_slice(slice_id)
    return applied.get("status") == "applied"


def _run_once_direct(tmp: Path) -> float | None:
    from fastapi.testclient import TestClient

    from e2e.harness.journey import JourneyClient
    from api.app import app

    ws = _prepare_workspace(tmp)
    t0 = time.perf_counter()
    with TestClient(app) as client:
        _bind_inmemory_chat(client)
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
        if not _complete_patch_slice(jc):
            return None
    return (time.perf_counter() - t0) * 1000.0


def _run_once_via_chat(tmp: Path) -> float | None:
    from fastapi.testclient import TestClient

    from e2e.harness.journey import JourneyClient
    from api.app import app

    ws = _prepare_workspace(tmp)
    t0 = time.perf_counter()
    with TestClient(app) as client:
        _bind_inmemory_chat(client)
        jc = JourneyClient(client=client)
        jc.attach_project(ws)
        session_resp = jc.client.post(
            "/v1/chat/sessions",
            json={"project_id": jc.project_id},
        )
        if session_resp.status_code != 200:
            return None
        session_id = session_resp.json().get("session_id")
        if not session_id:
            return None
        turn_resp = jc.client.post(
            f"/v1/chat/sessions/{session_id}/turns",
            json={"text": "Fix calculator test", "role": "user"},
        )
        if turn_resp.status_code != 200:
            return None
        start_resp = jc.client.post(
            f"/v1/chat/sessions/{session_id}/start",
            json={"work_type": "patch", "work_type_source": "classifier"},
        )
        if start_resp.status_code != 200:
            return None
        jc.run_id = str(start_resp.json().get("run_id") or "")
        if not jc.run_id:
            return None
        if not _complete_patch_slice(jc):
            return None
    return (time.perf_counter() - t0) * 1000.0


def _median(samples: list[float]) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0


def _measure(run_fn, tmp: Path, runs: int) -> list[float]:
    samples: list[float] = []
    for _ in range(max(1, runs)):
        delta = run_fn(tmp)
        if delta is not None:
            samples.append(delta)
    return samples


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path", default="")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument(
        "--via-chat",
        action="store_true",
        help="Measure chat turn → start → first slice.applied instead of direct /v1/runs",
    )
    args = parser.parse_args(argv)
    tmp = _REPO / ".cache" / "intent_to_patch_measure"
    if tmp.is_dir():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)

    run_fn = _run_once_via_chat if args.via_chat else _run_once_direct
    samples = _measure(run_fn, tmp, args.runs)
    median = _median(samples)
    body: dict[str, object] = {
        "ok": bool(samples),
        "sample_size": len(samples),
        "median_ms": median,
        "target_median_ms": 180_000,
        "meets_target": median is not None and median <= 180_000,
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fixture": "tests/fixtures/repos/tiny_python_app",
        "path": "chat" if args.via_chat else "direct",
    }
    if args.via_chat:
        body["chat_median_ms"] = median
    if args.json_path:
        out = Path(args.json_path)
        if out.is_file():
            try:
                prior = json.loads(out.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                prior = {}
            if isinstance(prior, dict):
                if args.via_chat:
                    prior["chat_median_ms"] = median
                    prior["chat_sample_size"] = len(samples)
                    prior["chat_meets_target"] = body["meets_target"]
                    prior["published_at"] = body["published_at"]
                else:
                    prior.update(body)
                body = prior
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(body, indent=2))
    return 0 if bool(samples) else 1


if __name__ == "__main__":
    raise SystemExit(main())
