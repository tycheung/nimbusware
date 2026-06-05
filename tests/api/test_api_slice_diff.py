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
def slice_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "README.md").write_text("# slice\n", encoding="utf-8")
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("NIMBUSWARE_WORKSPACE", str(ws))
    with TestClient(app) as c:
        yield c


def test_slice_diff_not_found_without_plan(slice_client: TestClient) -> None:
    rid = slice_client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    r = slice_client.get(f"/v1/runs/{rid}/slices/1/diff")
    assert r.status_code == 404
    assert r.json()["code"] == "slice_not_found"


def test_slice_diff_after_micro_slice_lifecycle(slice_client: TestClient) -> None:
    rid = slice_client.post("/v1/runs", json={"workflow_profile": "micro_slice"}).json()["run_id"]
    life = slice_client.post(f"/v1/runs/{rid}/lifecycle/slice")
    assert life.status_code == 200
    r = slice_client.get(f"/v1/runs/{rid}/slices/1/diff")
    assert r.status_code == 200
    data = r.json()
    assert data["slice_index"] == 1
    assert data["slice_id"]
