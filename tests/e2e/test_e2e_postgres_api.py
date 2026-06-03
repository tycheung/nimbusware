"""E2E API path with Postgres-backed event store."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")
os.environ.setdefault("NIMBUSWARE_ADMIN_TOKEN", DEFAULT_NIMBUSWARE_ADMIN_TOKEN)

from nimbusware_api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    if not os.environ.get("NIMBUSWARE_DATABASE_URL"):
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")
    with TestClient(app) as c:
        yield c


def test_create_run_has_run_created_in_timeline(client: TestClient) -> None:
    created = client.post("/v1/runs", json={"workflow_profile": "default"})
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    timeline = client.get(f"/v1/runs/{run_id}/timeline")
    assert timeline.status_code == 200
    types = [ev.get("event_type") for ev in timeline.json().get("events", [])]
    assert "run.created" in types
