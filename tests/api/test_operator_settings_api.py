from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from nimbusware_api.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_settings_catalog(client: TestClient) -> None:
    r = client.get("/v1/settings/catalog")
    assert r.status_code == 200
    body = r.json()
    assert "system" in body
    assert "user" in body


def test_patch_user_settings(client: TestClient) -> None:
    r = client.patch(
        "/v1/settings/me",
        json={"values": {"HERMES_SLICE_AUTO_ADVANCE": "0"}},
    )
    assert r.status_code == 200
    assert r.json()["values"]["HERMES_SLICE_AUTO_ADVANCE"] == "0"


def test_patch_system_requires_admin(client: TestClient) -> None:
    token = os.environ.get("NIMBUSWARE_ADMIN_TOKEN", "")
    r = client.patch(
        "/v1/settings/system",
        json={"values": {"HERMES_RERESARCH_MISSING_CONTEXT": "1"}},
        headers={"X-Nimbusware-Admin-Token": token},
    )
    assert r.status_code == 200
    assert r.json()["values"]["HERMES_RERESARCH_MISSING_CONTEXT"] == "1"
