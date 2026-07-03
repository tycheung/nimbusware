from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

ADMIN_HEADERS = {"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN}

pytestmark = pytest.mark.slow


def test_projects_crud(client: TestClient, tmp_path: Path) -> None:
    ws = tmp_path / "maker-app"
    ws.mkdir()
    create = client.post(
        "/v1/projects",
        json={
            "name": "Maker demo",
            "workspace_path": str(ws),
            "template": "attach",
            "default_workflow_profile": "micro_slice",
        },
    )
    assert create.status_code == 200
    project_id = create.json()["project_id"]

    listing = client.get("/v1/projects")
    assert listing.status_code == 200
    assert any(p["project_id"] == project_id for p in listing.json()["projects"])

    detail = client.get(f"/v1/projects/{project_id}")
    assert detail.status_code == 200
    assert detail.json()["workspace_path"] == str(ws.resolve())

    deleted = client.delete(f"/v1/projects/{project_id}", headers=ADMIN_HEADERS)
    assert deleted.status_code == 204
    assert client.get(f"/v1/projects/{project_id}").status_code == 404


def test_projects_patch(client: TestClient, tmp_path: Path) -> None:
    ws = tmp_path / "app-a"
    ws.mkdir()
    create = client.post(
        "/v1/projects",
        json={"name": "Alpha", "workspace_path": str(ws), "template": "attach"},
    )
    project_id = create.json()["project_id"]
    ws2 = tmp_path / "app-b"
    ws2.mkdir()
    patched = client.patch(
        f"/v1/projects/{project_id}",
        json={"name": "Beta", "workspace_path": str(ws2)},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["name"] == "Beta"
    assert body["workspace_path"] == str(ws2.resolve())


def test_projects_patch_empty_body_422(client: TestClient, tmp_path: Path) -> None:
    ws = tmp_path / "empty-patch"
    ws.mkdir()
    project_id = client.post(
        "/v1/projects",
        json={"name": "X", "workspace_path": str(ws), "template": "attach"},
    ).json()["project_id"]
    r = client.patch(f"/v1/projects/{project_id}", json={})
    assert r.status_code == 422


def test_create_run_with_project_id(client: TestClient, tmp_path: Path) -> None:
    ws = tmp_path / "proj-run"
    ws.mkdir()
    project = client.post(
        "/v1/projects",
        json={
            "name": "Run bind",
            "workspace_path": str(ws),
            "template": "attach",
        },
    ).json()
    run = client.post(
        "/v1/runs",
        json={
            "workflow_profile": "micro_slice",
            "project_id": project["project_id"],
        },
    )
    assert run.status_code == 200
    run_id = run.json()["run_id"]
    timeline = client.get(f"/v1/runs/{run_id}/timeline").json()
    created = timeline["events"][0]
    project_meta = (created.get("metadata") or {}).get("project") or {}
    assert project_meta.get("workspace_path") == str(ws.resolve())


def test_create_run_unknown_project_422(client: TestClient) -> None:
    r = client.post(
        "/v1/runs",
        json={
            "workflow_profile": "default",
            "project_id": "00000000-0000-4000-8000-000000009999",
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "project_not_found"
