from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


def _enable_collab(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_COLLAB_ENABLED", "1")
    from nimbusware_env.collab_runtime import set_runtime_collab_enabled

    set_runtime_collab_enabled(True)


def _signup(client: TestClient, username: str) -> dict:
    resp = client.post(
        "/v1/auth/signup",
        json={"username": username, "password": "password1234", "display_name": username.title()},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_collab_participant_bindings_route_per_user(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_collab(monkeypatch)
    host = _signup(client, f"host-bind-{uuid4().hex[:6]}")
    guest = _signup(client, f"guest-bind-{uuid4().hex[:6]}")
    ws = tmp_path / "bind-app"
    ws.mkdir()
    client.post(
        "/v1/auth/signin",
        json={"username": host["username"], "password": "password1234"},
    )
    project_id = client.post(
        "/v1/projects",
        json={
            "name": "bind",
            "workspace_path": str(ws),
            "template": "attach",
            "default_workflow_profile": "micro_slice",
        },
    ).json()["project_id"]
    session_id = client.post(
        "/v1/chat/sessions",
        json={"project_id": project_id},
    ).json()["session_id"]
    client.post(
        f"/v1/chat/sessions/{session_id}/participants",
        json={"user_id": guest["user_id"], "role": "session_write"},
    )

    host_put = client.put(
        f"/v1/chat/sessions/{session_id}/participant-bindings",
        json={
            "agent_role": "implementer",
            "provider_kind": "cloud",
            "provider_id": "openai",
            "model_id": "gpt-4o-mini",
        },
    )
    assert host_put.status_code == 200, host_put.text
    assert host_put.json()["roles"]["implementer"]["model_id"] == "gpt-4o-mini"

    client.post(
        "/v1/auth/signin",
        json={"username": guest["username"], "password": "password1234"},
    )
    guest_put = client.put(
        f"/v1/chat/sessions/{session_id}/participant-bindings",
        json={
            "agent_role": "implementer",
            "provider_kind": "local",
            "provider_id": "ollama",
            "model_id": "llama3.1:8b",
        },
    )
    assert guest_put.status_code == 200, guest_put.text

    client.post(
        "/v1/auth/signin",
        json={"username": host["username"], "password": "password1234"},
    )
    host_get = client.get(f"/v1/chat/sessions/{session_id}/participant-bindings")
    client.post(
        "/v1/auth/signin",
        json={"username": guest["username"], "password": "password1234"},
    )
    guest_get = client.get(f"/v1/chat/sessions/{session_id}/participant-bindings")
    assert host_get.json()["roles"]["implementer"]["provider_id"] == "openai"
    assert guest_get.json()["roles"]["implementer"]["provider_id"] == "ollama"
