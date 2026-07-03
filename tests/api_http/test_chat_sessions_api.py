from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.slow


def _create_project(client: TestClient, tmp_path: Path) -> str:
    ws = tmp_path / "chat-app"
    ws.mkdir()
    resp = client.post(
        "/v1/projects",
        json={
            "name": "Chat demo",
            "workspace_path": str(ws),
            "template": "attach",
            "default_workflow_profile": "micro_slice",
        },
    )
    assert resp.status_code == 200
    return resp.json()["project_id"]


def test_chat_session_lifecycle(client: TestClient, tmp_path: Path) -> None:
    project_id = _create_project(client, tmp_path)

    created = client.post("/v1/chat/sessions", json={"project_id": project_id})
    assert created.status_code == 200
    session_id = created.json()["session_id"]
    assert created.json()["project_id"] == project_id

    detail = client.get(f"/v1/chat/sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["messages"] == []

    msg = client.post(
        f"/v1/chat/sessions/{session_id}/messages",
        json={
            "text": "fix the failing test in tests/test_auth.py",
            "attachments": [{"failing_test": "tests/test_auth.py::test_login"}],
        },
    )
    assert msg.status_code == 200
    body = msg.json()
    assert body["classification"]["work_type"] == "patch"
    assert "patch" in body["classification"]["suggested_profile"]

    classify = client.post(
        "/v1/chat/classify",
        json={
            "message": "Build a CRM MVP",
            "project_id": project_id,
        },
    )
    assert classify.status_code == 200
    assert classify.json()["classification"]["work_type"] == "campaign"


def test_chat_start_slice_run(client: TestClient, tmp_path: Path) -> None:
    project_id = _create_project(client, tmp_path)
    session_id = client.post("/v1/chat/sessions", json={"project_id": project_id}).json()[
        "session_id"
    ]
    client.post(
        f"/v1/chat/sessions/{session_id}/messages",
        json={"text": "add feature for export endpoint"},
    )
    started = client.post(
        f"/v1/chat/sessions/{session_id}/start",
        json={"work_type": "slice"},
    )
    assert started.status_code == 200
    body = started.json()
    assert body["work_type"] == "slice"
    assert body["run_id"]
    assert body["campaign_id"] is None

    session = client.get(f"/v1/chat/sessions/{session_id}").json()
    assert session["run_id"] == body["run_id"]


def test_chat_start_patch_run(client: TestClient, tmp_path: Path) -> None:
    project_id = _create_project(client, tmp_path)
    session_id = client.post("/v1/chat/sessions", json={"project_id": project_id}).json()[
        "session_id"
    ]
    client.post(
        f"/v1/chat/sessions/{session_id}/messages",
        json={
            "text": "fix login bug",
            "attachments": [{"failing_test": "tests/test_login.py::test_ok"}],
        },
    )
    started = client.post(f"/v1/chat/sessions/{session_id}/start", json={})
    assert started.status_code == 200
    body = started.json()
    assert body["work_type"] == "patch"
    assert body["workflow_profile"] == "patch"
    assert body["run_id"]


def test_chat_session_not_found(client: TestClient) -> None:
    missing = client.get("/v1/chat/sessions/00000000-0000-0000-0000-000000000099")
    assert missing.status_code == 404
    assert missing.json()["code"] == "chat_session_not_found"


def test_chat_create_session_unknown_project_422(client: TestClient) -> None:
    resp = client.post(
        "/v1/chat/sessions",
        json={"project_id": "00000000-0000-0000-0000-000000000099"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "project_not_found"
