from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")

from nimbusware_api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_maker_web_index_served(client: TestClient) -> None:
    r = client.get("/v1/maker/app/")
    assert r.status_code == 200
    assert "run-theater-run-id" in r.text
    assert "Hermes Maker" in r.text
