from __future__ import annotations

import time
from pathlib import Path

import pytest

from e2e.harness.workspace import copy_fixture_repo

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_fixture_repo]

_TARGET_MS = 180_000


def test_chat_patch_intent_to_first_slice(journey_client, tmp_path: Path) -> None:
    ws = copy_fixture_repo("tiny_python_app", tmp_path / "chat-patch")
    (ws / "packages/orchestrator").mkdir(parents=True, exist_ok=True)
    (ws / "packages/orchestrator/micro_slice.py").write_text(
        "# stub\n", encoding="utf-8"
    )
    (ws / "packages/orchestrator/slice_gate.py").write_text("# stub\n", encoding="utf-8")

    journey_client.attach_project(ws, name="chat-patch-timing")
    t0 = time.perf_counter()

    session_resp = journey_client.client.post(
        "/v1/chat/sessions",
        json={"project_id": journey_client.project_id},
    )
    assert session_resp.status_code == 200, session_resp.text
    session_id = session_resp.json()["session_id"]

    turn_resp = journey_client.client.post(
        f"/v1/chat/sessions/{session_id}/turns",
        json={"text": "Fix the failing calculator unit test", "role": "user"},
    )
    assert turn_resp.status_code == 200, turn_resp.text
    classification = turn_resp.json().get("classification") or {}
    assert classification.get("work_type") == "patch"

    start_resp = journey_client.client.post(
        f"/v1/chat/sessions/{session_id}/start",
        json={"work_type": "patch", "work_type_source": "classifier"},
    )
    assert start_resp.status_code == 200, start_resp.text
    journey_client.run_id = str(start_resp.json().get("run_id") or "")
    assert journey_client.run_id

    pending = journey_client.get_pending()
    if pending.get("plan_approved") is False:
        journey_client.approve_plan()
    prep = journey_client.prepare_slice()
    assert prep.get("status") == "awaiting_approval", prep
    applied = journey_client.apply_slice(prep["pending"]["slice_id"])
    assert applied.get("status") == "applied", applied

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < _TARGET_MS, (
        f"chat patch path took {elapsed_ms:.0f}ms (target {_TARGET_MS}ms)"
    )
