"""Admin UI BFF: operator chat and formatted tables."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")

from nimbusware_api.app import app  # noqa: E402
from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

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


def test_operator_chat_help(client: TestClient) -> None:
    headers = {
        **ADMIN_HEADERS,
        "X-Nimbusware-Chat-Session": "test-session",
    }
    r = client.post(
        "/v1/admin/ui/operator-chat/message",
        json={"text": "/help"},
        headers=headers,
    )
    assert r.status_code == 200
    assert "Commands" in r.json()["reply"]


def test_findings_table_not_found(client: TestClient) -> None:
    rid = str(uuid4())
    r = client.get(
        f"/v1/admin/ui/runs/{rid}/findings-table",
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 404
