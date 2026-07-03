from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.slow


def _enable_collab(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_COLLAB_ENABLED", "1")


def _signup(client: TestClient, username: str) -> dict:
    resp = client.post(
        "/v1/auth/signup",
        json={"username": username, "password": "password1234", "display_name": username},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_project(client: TestClient, tmp_path: Path) -> str:
    ws = tmp_path / "lib-app"
    ws.mkdir()
    resp = client.post(
        "/v1/projects",
        json={
            "name": "lib",
            "workspace_path": str(ws),
            "template": "attach",
            "default_workflow_profile": "micro_slice",
        },
    )
    assert resp.status_code == 200
    return resp.json()["project_id"]


def test_chat_library_folders_grants_and_effective_role(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_collab(monkeypatch)
    admin = _signup(client, f"lib-admin-{uuid4().hex[:6]}")
    guest = _signup(client, f"lib-guest-{uuid4().hex[:6]}")
    client.post(
        "/v1/auth/signin",
        json={"username": admin["username"], "password": "password1234"},
    )
    project_id = _create_project(client, tmp_path)
    folder = client.post(
        "/v1/chat/folders",
        json={"project_id": project_id, "name": "Q2 patches"},
    )
    assert folder.status_code == 200, folder.text
    folder_id = folder.json()["folder"]["folder_id"]
    sess = client.post("/v1/chat/sessions", json={"project_id": project_id, "title": "lib"})
    assert sess.status_code == 200
    session_id = sess.json()["session_id"]
    move = client.put(
        f"/v1/chat/sessions/{session_id}/library",
        json={"folder_id": folder_id, "tags": ["security"]},
    )
    assert move.status_code == 200, move.text
    assert move.json()["session"]["folder_id"] == folder_id
    grant = client.post(
        "/v1/chat/access-grants",
        json={
            "grantee_type": "user",
            "grantee_user_id": guest["user_id"],
            "scope_type": "folder",
            "folder_id": folder_id,
            "participant_role": "session_write",
        },
    )
    assert grant.status_code == 200, grant.text
    eff = client.get(
        f"/v1/chat/sessions/{session_id}/effective-role",
        params={"target_user_id": guest["user_id"]},
    )
    data = eff.json()
    assert data["user_id"] == guest["user_id"]
    assert data["grant_roles"]["folder"] == ["session_write"]
    assert data["direct_role"] is None
    assert data["effective_role"] == "session_write"
    client.post("/v1/auth/signout")
    client.post(
        "/v1/auth/signin",
        json={"username": guest["username"], "password": "password1234"},
    )
    listed = client.get(f"/v1/chat/folders?project_id={project_id}")
    assert listed.status_code == 200
    assert len(listed.json()["folders"]) == 1
