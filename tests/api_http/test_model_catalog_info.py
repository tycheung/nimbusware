from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_catalog_info(client: TestClient) -> None:
    r = client.get("/v1/platform/models/catalog-info")
    assert r.status_code == 200
    body = r.json()
    assert body["model_count"] >= 1
    assert body["version"] >= 1
    assert "updated_at" in body
    assert body["source"] == "bundled"
