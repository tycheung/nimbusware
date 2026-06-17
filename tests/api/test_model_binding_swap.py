from __future__ import annotations

from fastapi.testclient import TestClient


def _create_run(client: TestClient) -> str:
    resp = client.post("/v1/runs", json={"workflow_profile": "default"})
    assert resp.status_code == 200, resp.text
    return str(resp.json()["run_id"])


def test_run_model_binding_swap(client: TestClient) -> None:
    run_id = _create_run(client)
    resp = client.post(
        f"/v1/runs/{run_id}/model-bindings/swap",
        json={
            "agent_role": "planner",
            "provider_id": "ollama",
            "provider_kind": "local",
            "model_id": "llama3.1:8b",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("ok") is True
    assert body.get("event") == "model.binding.overridden"
    assert body["payload"]["agent_role"] == "planner"
    assert body["payload"]["model_id"] == "llama3.1:8b"


def test_run_role_claim_and_release(client: TestClient) -> None:
    run_id = _create_run(client)
    claim = client.post(
        f"/v1/runs/{run_id}/role-claims",
        json={
            "agent_role": "backend_writer",
            "provider_id": "ollama",
            "model_id": "qwen2.5-coder:14b",
        },
    )
    assert claim.status_code == 200, claim.text
    assert claim.json().get("event") == "workload.role_claimed"

    release = client.delete(f"/v1/runs/{run_id}/role-claims/backend_writer")
    assert release.status_code == 200, release.text
    assert release.json().get("event") == "workload.role_released"
