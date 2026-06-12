from __future__ import annotations

from pathlib import Path

import pytest

from e2e.harness.workspace import copy_fixture_repo

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_fixture_repo]


def test_chat_mid_thread_patch_to_slice(journey_client, tmp_path: Path) -> None:
    ws = copy_fixture_repo("tiny_python_app", tmp_path / "chat-mid")
    (ws / "packages/nimbusware_orchestrator").mkdir(parents=True, exist_ok=True)
    (ws / "packages/nimbusware_orchestrator/micro_slice.py").write_text(
        "# stub\n", encoding="utf-8"
    )
    (ws / "packages/nimbusware_orchestrator/slice_gate.py").write_text("# stub\n", encoding="utf-8")

    journey_client.attach_project(ws, name="chat-mid-thread")
    project_id = journey_client.project_id
    assert project_id

    session_id = journey_client.client.post(
        "/v1/chat/sessions",
        json={"project_id": project_id},
    ).json()["session_id"]

    turn = journey_client.client.post(
        f"/v1/chat/sessions/{session_id}/turns",
        json={"text": "fix login test", "attachments": []},
    ).json()
    user_turn_id = turn["message"]["turn_id"]

    patch_start = journey_client.client.post(
        f"/v1/chat/sessions/{session_id}/start",
        json={"work_type": "patch"},
    )
    assert patch_start.status_code == 200
    patch_run_id = patch_start.json()["run_id"]

    widened = journey_client.client.post(
        f"/v1/chat/sessions/{session_id}/turns/{user_turn_id}/switch-mode",
        json={"work_type": "slice", "rationale": "Patch gate failed — micro-slice"},
    )
    assert widened.status_code == 200
    assert widened.json()["work_type_override"] == "slice"

    slice_start = journey_client.client.post(
        f"/v1/chat/sessions/{session_id}/start",
        json={"work_type": "slice"},
    )
    assert slice_start.status_code == 200
    slice_run_id = slice_start.json()["run_id"]
    assert slice_run_id != patch_run_id

    session = journey_client.client.get(
        f"/v1/chat/sessions/{session_id}?include_turns=true",
    ).json()
    kinds = [m.get("kind") for m in session.get("messages", [])]
    assert "work_type_switch" in kinds
