from __future__ import annotations

from fastapi.testclient import TestClient


def test_platform_hardware(client: TestClient) -> None:
    r = client.get("/v1/platform/hardware")
    assert r.status_code == 200
    body = r.json()
    assert "profile" in body
    assert "resource_governor" in body
    assert body["profile"]["tier"] in ("weak", "medium", "strong")


def test_platform_hardware_rescan(client: TestClient) -> None:
    r = client.post("/v1/platform/hardware/rescan", json={})
    assert r.status_code == 200
    assert "profile" in r.json()
