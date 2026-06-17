from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def _create_project(client: TestClient, tmp_path: Path) -> str:
    ws = tmp_path / "compute-app"
    ws.mkdir()
    resp = client.post(
        "/v1/projects",
        json={
            "name": "Compute demo",
            "workspace_path": str(ws),
            "template": "attach",
            "default_workflow_profile": "micro_slice",
        },
    )
    assert resp.status_code == 200
    return resp.json()["project_id"]


def test_register_and_heartbeat_compute_node(client: TestClient) -> None:
    reg = client.post(
        "/v1/compute/nodes/register",
        json={
            "host_label": "test-worker",
            "base_url": "http://127.0.0.1:9999",
            "display_name": "Test worker",
            "capabilities": {"tier": "strong"},
        },
    )
    assert reg.status_code == 200
    node = reg.json()["node"]
    node_id = node["node_id"]
    assert node["status"] == "online"
    assert node["host_label"] == "test-worker"

    beat = client.post(
        f"/v1/compute/nodes/{node_id}/heartbeat",
        json={"status": "degraded", "capabilities": {"tier": "strong", "load": 0.8}},
    )
    assert beat.status_code == 200
    updated = beat.json()["node"]
    assert updated["status"] == "degraded"
    assert updated["capabilities"]["load"] == 0.8


def test_heartbeat_unknown_node_404(client: TestClient) -> None:
    resp = client.post(
        "/v1/compute/nodes/00000000-0000-4000-8000-000000000099/heartbeat",
        json={"status": "online"},
    )
    assert resp.status_code == 404


def test_list_compute_nodes_for_session(client: TestClient, tmp_path: Path) -> None:
    project_id = _create_project(client, tmp_path)
    session_id = client.post("/v1/chat/sessions", json={"project_id": project_id}).json()[
        "session_id"
    ]
    reg = client.post(
        "/v1/compute/nodes/register",
        json={
            "session_id": session_id,
            "host_label": "session-worker",
            "base_url": "http://127.0.0.1:9998",
            "display_name": "Session worker",
        },
    )
    assert reg.status_code == 200
    listed = client.get("/v1/compute/nodes", params={"session_id": session_id})
    assert listed.status_code == 200
    nodes = listed.json()["nodes"]
    assert len(nodes) == 1
    assert nodes[0]["session_id"] == session_id


def test_session_compute_opt_in_stub(client: TestClient, tmp_path: Path) -> None:
    project_id = _create_project(client, tmp_path)
    session_id = client.post("/v1/chat/sessions", json={"project_id": project_id}).json()[
        "session_id"
    ]
    opt_in = client.post(
        f"/v1/chat/sessions/{session_id}/compute/opt-in",
        json={
            "enabled": True,
            "share_policy": "claim_only",
            "host_label": "guest-laptop",
            "base_url": "http://192.168.1.50:8787",
        },
    )
    assert opt_in.status_code == 200
    body = opt_in.json()
    assert body["enabled"] is True
    assert body["share_policy"] == "claim_only"
    assert body["node"]["session_id"] == session_id
