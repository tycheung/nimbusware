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


def test_list_chat_sessions(client: TestClient, tmp_path: Path) -> None:
    project_id = _create_project(client, tmp_path)
    client.post("/v1/chat/sessions", json={"project_id": project_id})
    listed = client.get(f"/v1/chat/sessions?project_id={project_id}")
    assert listed.status_code == 200
    assert len(listed.json()) >= 1
