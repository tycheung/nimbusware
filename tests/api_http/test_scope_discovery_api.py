from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import app
from env import find_repo_root

os.environ.setdefault(
    "NIMBUSWARE_REPO_ROOT", str(find_repo_root(start=Path(__file__).resolve().parents[1]))
)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_scope_discover_emits_questions(client: TestClient) -> None:
    resp = client.post(
        "/v1/chat/scope/discover",
        json={"business_prompt": "Build a todo app"},
    )
    assert resp.status_code == 200, resp.text
    scope = resp.json()["scope"]
    assert scope["discovery_complete"] is False
    assert len(scope["questions_emitted"]) >= 3


def test_scope_recommend_completes_discovery(client: TestClient) -> None:
    resp = client.post(
        "/v1/chat/scope/recommend",
        json={"business_prompt": "Build a todo app"},
    )
    assert resp.status_code == 200, resp.text
    scope = resp.json()["scope"]
    assert scope["discovery_complete"] is True
    assert "web" in scope["stack_manifest"]["surfaces"]
