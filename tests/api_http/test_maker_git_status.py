from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_maker_git_status_not_found(client: TestClient) -> None:
    rid = str(uuid4())
    r = client.get(f"/v1/runs/{rid}/maker/git-status")
    assert r.status_code == 404


def test_maker_git_status_empty_run(client: TestClient) -> None:
    create = client.post("/v1/runs", json={"workflow_profile": "default"})
    assert create.status_code in (200, 201)
    rid = create.json()["run_id"]
    r = client.get(f"/v1/runs/{rid}/maker/git-status")
    assert r.status_code == 200
    body = r.json()
    assert body["git_commit"] is None
    assert "git_outputs" in body
    assert body["git_outputs"].get("branch")
