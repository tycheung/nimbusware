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
    ws = tmp_path / "collab-app"
    ws.mkdir()
    resp = client.post(
        "/v1/projects",
        json={
            "name": "collab",
            "workspace_path": str(ws),
            "template": "attach",
            "default_workflow_profile": "micro_slice",
        },
    )
    assert resp.status_code == 200
    return resp.json()["project_id"]


def test_session_commentary_and_delegate_control(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_collab(monkeypatch)
    _signup(client, f"admin-{uuid4().hex[:8]}")
    writer = _signup(client, f"writer-{uuid4().hex[:8]}")
    project_id = _create_project(client, tmp_path)
    sess = client.post("/v1/chat/sessions", json={"project_id": project_id})
    assert sess.status_code == 200
    session_id = sess.json()["session_id"]
    client.post(
        f"/v1/chat/sessions/{session_id}/participants",
        json={"user_id": writer["user_id"], "role": "session_write"},
    )
    client.post(
        "/v1/auth/signin", json={"username": writer["username"], "password": "password1234"}
    )
    client.post(
        f"/v1/chat/sessions/{session_id}/compute/opt-in",
        json={
            "enabled": True,
            "share_policy": "claim_only",
            "host_label": "writer-laptop",
            "base_url": "http://127.0.0.1:8766",
        },
    )
    commentary = client.post(
        f"/v1/chat/sessions/{session_id}/commentary",
        json={"text": "Looks good from the gallery"},
    )
    assert commentary.status_code == 200, commentary.text
    assert commentary.json()["turn"]["role"] == "participant"
    delegate = client.post(
        f"/v1/chat/sessions/{session_id}/compute/delegate-control",
        json={"allow_host_resource_management": True},
    )
    assert delegate.status_code == 200, delegate.text
    assert delegate.json()["node"]["allow_host_resource_management"] is True


def test_host_transfer_decline(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_collab(monkeypatch)
    _signup(client, f"host-{uuid4().hex[:8]}")
    target = _signup(client, f"target-{uuid4().hex[:8]}")
    project_id = _create_project(client, tmp_path)
    sess = client.post("/v1/chat/sessions", json={"project_id": project_id})
    session_id = sess.json()["session_id"]
    client.post(
        f"/v1/chat/sessions/{session_id}/participants",
        json={"user_id": target["user_id"], "role": "session_admin"},
    )
    req = client.post(
        f"/v1/chat/sessions/{session_id}/host-transfer",
        json={"to_user_id": target["user_id"]},
    )
    assert req.status_code == 200
    transfer_id = req.json()["transfer"]["transfer_id"]
    client.post(
        "/v1/auth/signin", json={"username": target["username"], "password": "password1234"}
    )
    declined = client.post(f"/v1/chat/sessions/{session_id}/host-transfer/{transfer_id}/decline")
    assert declined.status_code == 200
    assert declined.json()["transfer"]["status"] == "declined"


def test_optimizer_weights_round_trip(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_collab(monkeypatch)
    user = _signup(client, f"opt-{uuid4().hex[:8]}")
    client.post("/v1/auth/signin", json={"username": user["username"], "password": "password1234"})
    put = client.put(
        "/v1/platform/optimizer-weights",
        json={"weights": {"headroom": 0.4, "model_fit": 0.3, "latency": 0.2, "cost": 0.1}},
    )
    assert put.status_code == 200
    got = client.get("/v1/platform/optimizer-weights")
    assert got.status_code == 200
    assert got.json()["weights"]["headroom"] == 0.4
