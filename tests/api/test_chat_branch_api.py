from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.slow


def _create_project(client: TestClient, tmp_path: Path) -> str:
    ws = tmp_path / "chat-branch"
    ws.mkdir()
    resp = client.post(
        "/v1/projects",
        json={
            "name": "Branch demo",
            "workspace_path": str(ws),
            "template": "attach",
        },
    )
    assert resp.status_code == 200
    return resp.json()["project_id"]


def test_chat_fork_and_graph(client: TestClient, tmp_path: Path) -> None:
    project_id = _create_project(client, tmp_path)
    session_id = client.post("/v1/chat/sessions", json={"project_id": project_id}).json()[
        "session_id"
    ]
    msg = client.post(
        f"/v1/chat/sessions/{session_id}/turns",
        json={"text": "fix auth test", "attachments": []},
    )
    assert msg.status_code == 200
    user_turn_id = msg.json()["message"]["turn_id"]

    forked = client.post(
        f"/v1/chat/sessions/{session_id}/fork",
        json={"turn_id": user_turn_id},
    )
    assert forked.status_code == 200
    assert forked.json()["active_leaf_turn_id"] == user_turn_id

    alt = client.post(
        f"/v1/chat/sessions/{session_id}/turns",
        json={"text": "build crm instead"},
    )
    assert alt.status_code == 200

    graph = client.get(f"/v1/chat/sessions/{session_id}/graph")
    assert graph.status_code == 200
    body = graph.json()
    assert len(body["nodes"]) >= 3
    assert body["branches"]


def test_chat_switch_mode(client: TestClient, tmp_path: Path) -> None:
    project_id = _create_project(client, tmp_path)
    session_id = client.post("/v1/chat/sessions", json={"project_id": project_id}).json()[
        "session_id"
    ]
    turn = client.post(
        f"/v1/chat/sessions/{session_id}/turns",
        json={"text": "small fix"},
    ).json()
    user_turn_id = turn["message"]["turn_id"]

    switched = client.post(
        f"/v1/chat/sessions/{session_id}/turns/{user_turn_id}/switch-mode",
        json={"work_type": "slice", "rationale": "Widen scope"},
    )
    assert switched.status_code == 200
    assert switched.json()["work_type_override"] == "slice"
    kinds = [m.get("kind") for m in switched.json()["messages"]]
    assert "work_type_switch" in kinds


def test_chat_switch_mode_records_replay_from_seq(client: TestClient, tmp_path: Path) -> None:
    project_id = _create_project(client, tmp_path)
    session_id = client.post("/v1/chat/sessions", json={"project_id": project_id}).json()[
        "session_id"
    ]
    turn = client.post(
        f"/v1/chat/sessions/{session_id}/turns",
        json={"text": "widen after gate fail"},
    ).json()
    user_turn_id = turn["message"]["turn_id"]

    switched = client.post(
        f"/v1/chat/sessions/{session_id}/turns/{user_turn_id}/switch-mode",
        json={
            "work_type": "slice",
            "rationale": "Align run replay",
            "align_run_replay": True,
            "replay_from_seq": 42,
        },
    )
    assert switched.status_code == 200
    switch_turns = [
        t for t in switched.json().get("turns") or [] if t.get("role") == "work_type_switch"
    ]
    assert switch_turns
    payload = (switch_turns[-1].get("payload") or {}) if switch_turns else {}
    assert payload.get("replay_from_seq") == 42


def test_chat_mid_thread_patch_to_slice_journey(client: TestClient, tmp_path: Path) -> None:
    """Same session: patch turn, widen to slice via switch-mode, then start slice run."""
    project_id = _create_project(client, tmp_path)
    session_id = client.post("/v1/chat/sessions", json={"project_id": project_id}).json()[
        "session_id"
    ]
    turn = client.post(
        f"/v1/chat/sessions/{session_id}/turns",
        json={"text": "fix login test", "attachments": []},
    ).json()
    user_turn_id = turn["message"]["turn_id"]

    patch_start = client.post(
        f"/v1/chat/sessions/{session_id}/start",
        json={"work_type": "patch"},
    )
    assert patch_start.status_code == 200
    patch_run_id = patch_start.json()["run_id"]

    widened = client.post(
        f"/v1/chat/sessions/{session_id}/turns/{user_turn_id}/switch-mode",
        json={"work_type": "slice", "rationale": "Patch gate failed — micro-slice"},
    )
    assert widened.status_code == 200
    assert widened.json()["work_type_override"] == "slice"

    slice_start = client.post(
        f"/v1/chat/sessions/{session_id}/start",
        json={"work_type": "slice"},
    )
    assert slice_start.status_code == 200
    slice_run_id = slice_start.json()["run_id"]
    assert slice_run_id != patch_run_id

    session = client.get(f"/v1/chat/sessions/{session_id}?include_turns=true").json()
    kinds = [m.get("kind") for m in session.get("messages", [])]
    assert "work_type_switch" in kinds


def test_chat_start_applies_replay_alignment(client: TestClient, tmp_path: Path) -> None:
    project_id = _create_project(client, tmp_path)
    session_id = client.post("/v1/chat/sessions", json={"project_id": project_id}).json()[
        "session_id"
    ]
    client.post(
        f"/v1/chat/sessions/{session_id}/turns",
        json={"text": "align replay on start"},
    )

    started = client.post(
        f"/v1/chat/sessions/{session_id}/start",
        json={
            "work_type": "patch",
            "align_run_replay": True,
            "replay_from_seq": 7,
        },
    )
    assert started.status_code == 200
    body = started.json()
    assert body["replay_alignment"]["from_store_seq"] == 7
    assert body["replay_alignment"]["replay_started"] is True
    run_id = body["run_id"]
    timeline = client.get(f"/v1/runs/{run_id}/timeline")
    assert timeline.status_code == 200
    replay_stages = [
        ev
        for ev in timeline.json().get("events") or []
        if (ev.get("payload") or {}).get("stage_name") == "run.replay.started"
    ]
    assert replay_stages
    assert replay_stages[-1]["metadata"]["from_store_seq"] == 7


def test_chat_start_inherits_replay_from_switch_mode(client: TestClient, tmp_path: Path) -> None:
    project_id = _create_project(client, tmp_path)
    session_id = client.post("/v1/chat/sessions", json={"project_id": project_id}).json()[
        "session_id"
    ]
    turn = client.post(
        f"/v1/chat/sessions/{session_id}/turns",
        json={"text": "widen with replay"},
    ).json()
    user_turn_id = turn["message"]["turn_id"]

    switched = client.post(
        f"/v1/chat/sessions/{session_id}/turns/{user_turn_id}/switch-mode",
        json={
            "work_type": "slice",
            "align_run_replay": True,
            "replay_from_seq": 11,
        },
    )
    assert switched.status_code == 200

    started = client.post(
        f"/v1/chat/sessions/{session_id}/start",
        json={"work_type": "slice"},
    )
    assert started.status_code == 200
    body = started.json()
    assert body["replay_alignment"]["from_store_seq"] == 11
    assert body["replay_alignment"]["replay_started"] is True


def test_list_chat_sessions(client: TestClient, tmp_path: Path) -> None:
    project_id = _create_project(client, tmp_path)
    client.post("/v1/chat/sessions", json={"project_id": project_id})
    listed = client.get(f"/v1/chat/sessions?project_id={project_id}")
    assert listed.status_code == 200
    assert len(listed.json()) >= 1
