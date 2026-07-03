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
        json={
            "username": username,
            "password": "password1234",
            "display_name": username,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_project(client: TestClient, tmp_path: Path) -> str:
    ws = tmp_path / "xfer-app"
    ws.mkdir()
    resp = client.post(
        "/v1/projects",
        json={
            "name": "xfer",
            "workspace_path": str(ws),
            "template": "attach",
            "default_workflow_profile": "micro_slice",
        },
    )
    assert resp.status_code == 200
    return resp.json()["project_id"]


def test_host_transfer_freeze_bundle_and_complete(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_collab(monkeypatch)
    admin_name = f"admin-{uuid4().hex[:6]}"
    target_name = f"target-{uuid4().hex[:6]}"
    _signup(client, admin_name)
    target = _signup(client, target_name)
    client.post(
        "/v1/auth/signin",
        json={"username": admin_name, "password": "password1234"},
    )
    project_id = _create_project(client, tmp_path)
    sess = client.post("/v1/chat/sessions", json={"project_id": project_id, "title": "xfer"})
    assert sess.status_code == 200
    session_id = sess.json()["session_id"]
    req = client.post(
        f"/v1/chat/sessions/{session_id}/host-transfer",
        json={"to_user_id": target["user_id"]},
    )
    assert req.status_code == 200, req.text
    transfer_id = req.json()["transfer"]["transfer_id"]
    client.post("/v1/auth/signout")
    client.post(
        "/v1/auth/signin",
        json={"username": target_name, "password": "password1234"},
    )
    accept = client.post(f"/v1/chat/sessions/{session_id}/host-transfer/{transfer_id}/accept")
    assert accept.status_code == 200, accept.text
    assert accept.json()["transfer"]["status"] == "frozen"
    bundle = client.get(f"/v1/chat/sessions/{session_id}/host-transfer/{transfer_id}/bundle")
    assert bundle.status_code == 200, bundle.text
    assert bundle.json()["manifest"]["checksum_sha256"]
    imported = client.post(
        f"/v1/chat/sessions/{session_id}/host-transfer/{transfer_id}/import",
        json={"manifest": bundle.json()["manifest"]},
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["transfer"]["status"] == "completed"
    refreshed = client.get(f"/v1/chat/sessions/{session_id}")
    assert refreshed.status_code == 200
    assert refreshed.json().get("host_user_id") == target["user_id"]
