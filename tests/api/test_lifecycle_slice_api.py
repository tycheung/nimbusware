"""POST /v1/runs/{id}/lifecycle/slice API."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nimbusware_env import find_repo_root

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault("NIMBUSWARE_MICRO_SLICE_COUNT", "1")

from nimbusware_api.app import app  # noqa: E402

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))
    with TestClient(app) as c:
        yield c


def test_lifecycle_slice_endpoint(client: TestClient) -> None:
    created = client.post("/v1/runs", json={"workflow_profile": "micro_slice"})
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    resp = client.post(f"/v1/runs/{run_id}/lifecycle/slice?mode=auto")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "micro_slice_recorded"
    assert body["slices_completed"] + body["slices_blocked"] >= 1
