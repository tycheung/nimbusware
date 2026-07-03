from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _create_git_project(client: TestClient, tmp_path: Path) -> tuple[str, str]:
    ws = tmp_path / "git-ws"
    ws.mkdir()
    (ws / ".git").mkdir()
    resp = client.post(
        "/v1/projects",
        json={"name": "Git soak", "workspace_path": str(ws), "template": "attach"},
    )
    assert resp.status_code == 200
    project_id = resp.json()["project_id"]
    run_resp = client.post(
        "/v1/runs",
        json={"workflow_profile": "micro_slice", "project_id": project_id},
    )
    assert run_resp.status_code == 200
    return project_id, run_resp.json()["run_id"]


def test_maker_open_pr_created(client: TestClient, tmp_path: Path) -> None:
    _, run_id = _create_git_project(client, tmp_path)
    pr_url = "https://github.com/example/nimbusware/pull/1"
    with patch(
        "api.routes.runs.maker_approval.maybe_open_gh_pr",
        return_value={"status": "created", "pr_url": pr_url},
    ):
        resp = client.post(f"/v1/runs/{run_id}/maker/open-pr")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == run_id
    assert body["pr"]["status"] == "created"
    assert body["pr"]["pr_url"] == pr_url


def test_maker_open_pr_fails_without_gh(client: TestClient, tmp_path: Path) -> None:
    _, run_id = _create_git_project(client, tmp_path)
    with patch(
        "api.routes.runs.maker_approval.maybe_open_gh_pr",
        return_value={"status": "error", "reason": "gh_not_found"},
    ):
        resp = client.post(f"/v1/runs/{run_id}/maker/open-pr")
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "git_pr_failed"
