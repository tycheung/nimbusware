"""GET /v1/runs/{id}/memory-influence for Maker web progress panel."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from nimbusware_api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_memory_influence_run_not_found(client: TestClient) -> None:
    rid = str(uuid4())
    resp = client.get(f"/v1/runs/{rid}/memory-influence")
    assert resp.status_code == 404


def test_memory_influence_empty_run(client: TestClient) -> None:
    create = client.post(
        "/v1/runs",
        json={"workflow_profile": "default"},
    )
    assert create.status_code in (200, 201)
    rid = create.json()["run_id"]
    resp = client.get(f"/v1/runs/{rid}/memory-influence")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == rid
    assert body["rows"] == []
