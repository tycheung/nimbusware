from __future__ import annotations

from fastapi.testclient import TestClient


def test_provider_presets(client: TestClient) -> None:
    resp = client.get("/v1/platform/provider-presets")
    assert resp.status_code == 200
    body = resp.json()
    providers = body.get("providers")
    assert isinstance(providers, list)
    assert any(p.get("id") == "google" for p in providers)
