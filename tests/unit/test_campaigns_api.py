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


def test_post_campaigns_creates_run(client: TestClient, tmp_path: Path) -> None:
    ws = tmp_path / "campaign-project"
    ws.mkdir()
    project = client.post(
        "/v1/projects",
        json={
            "name": "Campaign test project",
            "workspace_path": str(ws),
            "template": "attach",
        },
    )
    assert project.status_code == 200, project.text
    project_id = project.json()["project_id"]
    resp = client.post(
        "/v1/campaigns",
        json={
            "project_id": project_id,
            "requirements": {
                "business_prompt": "Build a hello service",
                "recommend_for_me": True,
            },
            "autonomous": True,
            "workflow_profile": "campaign_fullstack",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("run_id")
    assert body.get("campaign_id") == body.get("run_id")
    assert body.get("workflow_profile") == "campaign_fullstack"


def test_post_campaigns_blocks_fullstack_without_discovery(
    client: TestClient, tmp_path: Path
) -> None:
    ws = tmp_path / "campaign-gate"
    ws.mkdir()
    project = client.post(
        "/v1/projects",
        json={
            "name": "Campaign gate project",
            "workspace_path": str(ws),
            "template": "attach",
        },
    )
    assert project.status_code == 200, project.text
    project_id = project.json()["project_id"]
    resp = client.post(
        "/v1/campaigns",
        json={
            "project_id": project_id,
            "requirements": {"business_prompt": "Build a todo app"},
            "autonomous": True,
            "workflow_profile": "campaign_fullstack",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "discovery_incomplete"
