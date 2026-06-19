import pytest
from fastapi.testclient import TestClient


def test_session_optimizer_weights_round_trip(client: TestClient, tmp_path) -> None:
    ws = tmp_path / "opt"
    ws.mkdir()
    project = client.post(
        "/v1/projects",
        json={"name": "opt-proj", "workspace_path": str(ws), "template": "attach"},
    )
    assert project.status_code == 200
    project_id = project.json()["project_id"]
    session = client.post("/v1/chat/sessions", json={"project_id": project_id})
    assert session.status_code == 200
    session_id = session.json()["session_id"]
    put = client.put(
        f"/v1/chat/sessions/{session_id}/optimizer-weights",
        json={"priority": ["latency", "headroom", "cost", "model_fit"]},
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["priority"][0] == "latency"
    assert body["weights"]["latency"] > body["weights"]["model_fit"]
    get = client.get(f"/v1/chat/sessions/{session_id}/optimizer-weights")
    assert get.status_code == 200
    assert get.json()["priority"][0] == "latency"
