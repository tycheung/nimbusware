from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")

from nimbusware_api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_maker_bootstrap_json(client: TestClient) -> None:
    r = client.get("/v1/maker/app/bootstrap.json")
    assert r.status_code == 200
    body = r.json()
    assert "api_base" in body
    assert "edition" in body
    assert body["features"]["maker_web"] is True


def test_admin_bootstrap_json(client: TestClient) -> None:
    r = client.get("/v1/admin/app/bootstrap.json")
    assert r.status_code == 200
    assert r.json()["admin_token_required"] is True
