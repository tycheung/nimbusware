from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_compute_node_register_and_heartbeat(client: TestClient) -> None:
    reg = client.post(
        "/v1/compute/nodes/register",
        json={
            "host_label": "journey-worker",
            "base_url": "http://127.0.0.1:9999",
            "display_name": "journey-worker",
            "capabilities": {"gpu": False},
        },
    )
    assert reg.status_code == 200, reg.text
    node_id = reg.json()["node"]["node_id"]
    beat = client.post(
        f"/v1/compute/nodes/{node_id}/heartbeat",
        json={"status": "online"},
    )
    assert beat.status_code == 200, beat.text
    assert beat.json()["node"]["status"] == "online"


def test_session_compute_opt_in(client: TestClient) -> None:
    proj = client.post("/v1/projects", json={"name": "mesh-journey", "workspace_path": "."})
    assert proj.status_code == 200
    project_id = proj.json()["project_id"]
    sess = client.post("/v1/chat/sessions", json={"project_id": project_id})
    assert sess.status_code == 200
    session_id = sess.json()["session_id"]
    opt = client.post(
        f"/v1/chat/sessions/{session_id}/compute/opt-in",
        json={"enabled": True, "share_policy": "claim_only"},
    )
    assert opt.status_code == 200, opt.text
    assert opt.json().get("enabled") is True
