from __future__ import annotations

from fastapi.testclient import TestClient


def test_routing_presets_list(client: TestClient) -> None:
    r = client.get("/v1/platform/routing-presets")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body.get("presets"), list)
    assert body.get("active_preset_id")
    assert "cloud_preflight" in body


def test_routing_presets_apply_local_only(client: TestClient) -> None:
    r = client.post(
        "/v1/platform/routing-presets/apply",
        json={"preset_id": "local_only"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["preset_id"] == "local_only"
    assert body["cloud_enabled"] is False


def test_routing_presets_apply_invalid(client: TestClient) -> None:
    r = client.post(
        "/v1/platform/routing-presets/apply",
        json={"preset_id": "not_a_real_preset"},
    )
    assert r.status_code == 422
