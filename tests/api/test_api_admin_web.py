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


def test_admin_web_index_when_built(client: TestClient) -> None:
    r = client.get("/v1/admin/app/")
    if r.status_code == 404:
        pytest.skip("admin dist not built")
    assert r.status_code == 200
    assert "Nimbusware Admin" in r.text or "app" in r.text
