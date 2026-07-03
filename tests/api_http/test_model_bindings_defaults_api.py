from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parents[2]


def test_model_binding_defaults_get(client: TestClient) -> None:
    resp = client.get("/v1/platform/model-bindings/defaults")
    assert resp.status_code == 200
    body = resp.json()
    assert "defaults" in body
    assert isinstance(body.get("roles"), list)


def test_model_binding_roles_get(client: TestClient) -> None:
    resp = client.get("/v1/platform/model-bindings/roles")
    assert resp.status_code == 200
    roles = resp.json().get("roles")
    assert isinstance(roles, list)
    assert any(r.get("agent_role") == "planner" for r in roles)


def test_model_binding_defaults_put(client: TestClient) -> None:
    payload = {
        "version": 1,
        "roles": {
            "planner": {
                "provider_kind": "local",
                "provider_id": "ollama",
                "model_id": "llama3.1:8b",
            },
        },
    }
    resp = client.put("/v1/platform/model-bindings/defaults", json=payload)
    assert resp.status_code == 200
    assert resp.json()["defaults"]["roles"]["planner"]["model_id"] == "llama3.1:8b"
