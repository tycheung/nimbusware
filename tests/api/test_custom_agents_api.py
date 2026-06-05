"""Custom agents HTTP API."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nimbusware_env import find_repo_root

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault(
    "NIMBUSWARE_ADMIN_TOKEN", "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
)

from nimbusware_api.app import app  # noqa: E402

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))
    with TestClient(app) as c:
        yield c


def test_list_custom_agents(client: TestClient) -> None:
    resp = client.get("/v1/custom-agents")
    assert resp.status_code == 200
    agents = resp.json()["agents"]
    assert any(a["id"] == "default_planner" for a in agents)


def test_delete_custom_agent(client: TestClient) -> None:
    create = client.post(
        "/v1/custom-agents",
        headers={
            "X-Nimbusware-Admin-Token": os.environ.get(
                "NIMBUSWARE_ADMIN_TOKEN",
                "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD",
            )
        },
        json={
            "id": "temp_agent",
            "display_name": "Temp",
            "system_prompt": "temporary",
        },
    )
    assert create.status_code == 200
    deleted = client.delete(
        "/v1/custom-agents/temp_agent",
        headers={
            "X-Nimbusware-Admin-Token": os.environ.get(
                "NIMBUSWARE_ADMIN_TOKEN",
                "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD",
            )
        },
    )
    assert deleted.status_code == 204
    missing = client.get("/v1/custom-agents/temp_agent")
    assert missing.status_code == 404


def test_create_run_with_custom_agent(client: TestClient) -> None:
    resp = client.post(
        "/v1/runs",
        json={"workflow_profile": "default", "custom_agent_id": "default_planner"},
    )
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]
    detail = client.get(f"/v1/runs/{run_id}/timeline")
    assert detail.status_code == 200
    body = detail.json()
    assert body.get("custom_agent", {}).get("id") == "default_planner"
