"""Fast in-process checks used by ``scripts/e2e_smoke.py`` (app profile)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from nimbusware_api.app import app

pytestmark = pytest.mark.e2e


@pytest.fixture
def client() -> TestClient:
    os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")
    with TestClient(app) as c:
        yield c


def test_api_create_run_timeline(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    t = client.get(f"/v1/runs/{run_id}/timeline")
    assert t.status_code == 200
    assert len(t.json().get("events", [])) >= 1


def test_console_app_importable() -> None:
    import importlib.util

    assert importlib.util.find_spec("nimbusware_console.app") is not None
