from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")
os.environ["NIMBUSWARE_HW_FIXTURE"] = "medium"

from nimbusware_api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_models_ranked(client: TestClient) -> None:
    r = client.get("/v1/platform/models/ranked", params={"use_case": "coding", "limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert body.get("use_case") == "coding"
    assert isinstance(body.get("models"), list)


def test_models_ranked_gpu_only(client: TestClient) -> None:
    r = client.get("/v1/platform/models/ranked", params={"gpu_only": True})
    assert r.status_code == 200
