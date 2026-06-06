from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nimbusware_api.app import app
from nimbusware_env import find_repo_root

os.environ.setdefault(
    "NIMBUSWARE_REPO_ROOT", str(find_repo_root(start=Path(__file__).resolve().parents[1]))
)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_post_campaigns_creates_run(client: TestClient) -> None:
    projects = client.get("/v1/projects").json()
    project_list = projects.get("projects") or []
    if not project_list:
        pytest.skip("no projects configured")
    project_id = project_list[0]["project_id"]
    resp = client.post(
        "/v1/campaigns",
        json={
            "project_id": project_id,
            "requirements": {"business_prompt": "Build a hello service"},
            "autonomous": True,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("run_id")
    assert body.get("campaign_id") == body.get("run_id")
