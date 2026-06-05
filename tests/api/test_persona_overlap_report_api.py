from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from nimbusware_api.app import app
from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

ADMIN_HEADERS = {
    "X-Nimbusware-Admin-Token": os.environ.get(
        "NIMBUSWARE_ADMIN_TOKEN",
        DEFAULT_NIMBUSWARE_ADMIN_TOKEN,
    ),
}


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_overlap_report_requires_admin(client: TestClient) -> None:
    r = client.get("/v1/personas/overlap-report")
    assert r.status_code == 401


def test_overlap_report_admin(client: TestClient) -> None:
    r = client.get("/v1/personas/overlap-report", headers=ADMIN_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "rows" in body
    assert "pair_count" in body


def test_overlap_report_bff(client: TestClient) -> None:
    r = client.get("/v1/admin/ui/personas/overlap-report", headers=ADMIN_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "rows" in body
