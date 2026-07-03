from __future__ import annotations

import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from env import find_repo_root
from env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault("NIMBUSWARE_ADMIN_TOKEN", DEFAULT_NIMBUSWARE_ADMIN_TOKEN)

from api.app import app  # noqa: E402

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])
ADMIN_HEADERS = {"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))
    with TestClient(app) as c:
        yield c


def test_list_ollama_models(client: TestClient) -> None:
    with (
        patch("api.routes.ollama.ollama_reachable", return_value=True),
        patch("api.routes.ollama.list_installed_models", return_value=[]),
    ):
        r = client.get("/v1/platform/ollama/models")
    assert r.status_code == 200
    body = r.json()
    assert body["reachable"] is True
    assert body["user_policy"]["allow_pull"] is False


def test_user_pull_forbidden_by_default(client: TestClient) -> None:
    r = client.post("/v1/platform/ollama/pull", json={"model": "llama3.1:8b"})
    assert r.status_code == 403


def test_admin_patch_user_policy(client: TestClient) -> None:
    r = client.patch(
        "/v1/admin/ollama/user-policy",
        json={
            "allow_pull": True,
            "allow_delete": False,
            "allow_update_routing": True,
        },
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["allow_pull"] is True
    assert body["allow_update_routing"] is True
    assert body.get("updated_at")
    with (
        patch("api.routes.ollama.ollama_reachable", return_value=True),
        patch("api.routes.ollama.list_installed_models", return_value=[]),
    ):
        cfg = client.get("/v1/platform/ollama/models")
    assert cfg.json()["user_policy"]["allow_pull"] is True


def test_user_pull_allowed_after_policy(client: TestClient) -> None:
    client.patch(
        "/v1/admin/ollama/user-policy",
        json={"allow_pull": True, "allow_delete": False, "allow_update_routing": False},
        headers=ADMIN_HEADERS,
    )
    with patch("api.routes.ollama.start_pull_job") as start_job:
        from orchestrator.routing.pull_jobs import PullJob

        start_job.return_value = PullJob(
            job_id="job-1", model="tiny", host="http://127.0.0.1:11434"
        )
        r = client.post("/v1/platform/ollama/pull", json={"model": "tiny"})
    assert r.status_code == 200
    assert r.json()["job_id"] == "job-1"
    assert r.json()["status"] == "accepted"
    start_job.assert_called_once()


def test_get_ollama_pull_job_status(client: TestClient) -> None:
    from orchestrator.routing.pull_jobs import PullJob, reset_pull_jobs_for_tests

    reset_pull_jobs_for_tests()
    with patch("api.routes.ollama.get_pull_job") as get_job:
        get_job.return_value = PullJob(
            job_id="job-1",
            model="tiny",
            host="http://127.0.0.1:11434",
            status="succeeded",
        )
        r = client.get("/v1/platform/ollama/pull/job-1")
    assert r.status_code == 200
    assert r.json()["status"] == "succeeded"


def test_filter_query_param(client: TestClient) -> None:
    from orchestrator.routing.manage import OllamaModelRow

    rows = [
        OllamaModelRow(name="llama3.1:8b"),
        OllamaModelRow(name="qwen2.5:7b"),
    ]

    def _filter(models: list, query: str) -> list:
        q = query.lower()
        return [m for m in models if q in m.name.lower()]

    with (
        patch("api.routes.ollama.ollama_reachable", return_value=True),
        patch("api.routes.ollama.list_installed_models", return_value=rows),
        patch("api.routes.ollama.filter_models", side_effect=_filter),
    ):
        r = client.get("/v1/platform/ollama/models", params={"q": "llama"})
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "llama"
    assert len(body["models"]) == 1
    assert body["models"][0]["name"] == "llama3.1:8b"
