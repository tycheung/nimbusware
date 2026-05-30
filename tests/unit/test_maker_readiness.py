from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_store.memory import InMemoryEventStore
from nimbusware_maker.readiness import build_platform_readiness
from nimbusware_maker.workspace import (
    project_metadata_block,
    resolve_run_workspace,
    workspace_path_from_run_created_metadata,
)


def test_workspace_from_metadata() -> None:
    meta = {
        "project": {
            "id": "00000000-0000-4000-8000-000000000099",
            "workspace_path": "C:/tmp/demo",
        },
    }
    assert workspace_path_from_run_created_metadata(meta) == Path("C:/tmp/demo").resolve()


def test_resolve_run_workspace_prefers_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HERMES_WORKSPACE", raising=False)
    rows = [
        {
            "event_type": "run.created",
            "metadata": {
                "project": {"workspace_path": str(tmp_path)},
            },
        },
    ]
    assert resolve_run_workspace(rows) == tmp_path.resolve()


def test_build_platform_readiness_in_memory_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HERMES_SKIP_PREFLIGHT", "1")
    repo = tmp_path
    (repo / "configs").mkdir()
    (repo / "configs" / "model-routing.yaml").write_text(
        "runtime:\n  base_url: http://127.0.0.1:11434\n",
        encoding="utf-8",
    )
    (repo / "configs" / "roles.yaml").write_text("roles: []\n", encoding="utf-8")
    body = build_platform_readiness(repo_root=repo, store=InMemoryEventStore())
    assert body["status"] in {"degraded", "not_ready", "ready"}
    assert body["checks"]["database"]["status"] == "degraded"
    assert body["checks"]["ollama"]["skipped"] is True
    assert "memory" in body["checks"]


@pytest.fixture
def client() -> TestClient:
    from nimbusware_api.app import app

    with TestClient(app) as c:
        yield c


def test_platform_readiness_endpoint(client: TestClient) -> None:
    r = client.get("/v1/platform/readiness")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body
    assert "checks" in body
    assert "ollama" in body["checks"]


def test_project_metadata_block() -> None:
    from uuid import UUID

    block = project_metadata_block(
        project_id=UUID("00000000-0000-4000-8000-000000000099"),
        name="Demo",
        workspace_path=Path("/tmp/demo"),
        template="attach",
    )
    assert block["name"] == "Demo"
    assert block["template"] == "attach"
