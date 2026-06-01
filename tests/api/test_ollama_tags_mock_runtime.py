"""Ollama list endpoint against a mock /api/tags response."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from nimbusware_env import find_repo_root

os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")

from nimbusware_api.app import app  # noqa: E402

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))
    with TestClient(app) as c:
        yield c


def test_list_models_uses_mock_tags_payload(client: TestClient) -> None:
    payload = {"models": [{"name": "mock:latest", "size": 42}]}
    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.read.return_value = json.dumps(payload).encode()

    with (
        patch("nimbusware_api.routes.ollama.ollama_reachable", return_value=True),
        patch("urllib.request.urlopen", return_value=mock_resp),
    ):
        r = client.get("/v1/platform/ollama/models")
    assert r.status_code == 200
    names = [m["name"] for m in r.json()["models"]]
    assert "mock:latest" in names
