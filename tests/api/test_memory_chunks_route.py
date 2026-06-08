"""GET /v1/memory/chunks — Maker memory library."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def test_memory_chunks_empty_for_unknown_project(client: TestClient) -> None:
    resp = client.get(f"/v1/memory/chunks?project_id={uuid4()}")
    assert resp.status_code == 404


def test_memory_chunks_lists_for_project(client: TestClient) -> None:
    project = client.post(
        "/v1/projects",
        json={
            "name": "mem-lib-test",
            "workspace_path": ".",
            "template": "attach",
        },
    )
    assert project.status_code == 200
    project_id = project.json()["project_id"]
    resp = client.get(f"/v1/memory/chunks?project_id={project_id}&limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_id"] == project_id
    assert "chunks" in body
    assert isinstance(body["chunks"], list)
