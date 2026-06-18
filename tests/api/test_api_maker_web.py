from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from nimbusware_api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_maker_web_index_served(client: TestClient) -> None:
    r = client.get("/v1/maker/app/")
    assert r.status_code == 200
    assert "run-theater-run-id" in r.text
    assert "Nimbusware Maker" in r.text
    assert "alpine.min.js" in r.text or "app-shell" in r.text


def test_ui_shared_modules_served(client: TestClient) -> None:
    r = client.get("/v1/nimbusware_ui_shared/js/api-core.js")
    assert r.status_code == 200
    assert "parseApiErrorBody" in r.text
    assert "fetchJson" in r.text
