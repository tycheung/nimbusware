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


def test_model_dependencies(client: TestClient) -> None:
    r = client.get("/v1/platform/models/dependencies")
    assert r.status_code == 200
    body = r.json()
    assert "ollama_reachable" in body
    assert "checks" in body
