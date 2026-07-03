from __future__ import annotations

from fastapi.testclient import TestClient


def test_model_bindings_preflight(client: TestClient) -> None:
    resp = client.get("/v1/platform/model-bindings/preflight", params={"probe": "false"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("roles_total", 0) >= 1
    assert "inference_mode" in body
    assert "roles_without_provider" in body
