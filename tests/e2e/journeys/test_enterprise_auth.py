from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from e2e.harness.env import apply_e2e_unit_profile
from env import find_repo_root

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey]


@pytest.fixture
def enterprise_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    repo = find_repo_root()
    apply_e2e_unit_profile(
        monkeypatch,
        repo_root=str(repo),
        extra={"NIMBUSWARE_EDITION": "enterprise"},
    )
    os.environ["NIMBUSWARE_EDITION"] = "enterprise"
    from api.app import app

    with TestClient(app) as client:
        yield client


def test_enterprise_status_without_bootstrap(enterprise_client: TestClient) -> None:
    resp = enterprise_client.get("/v1/enterprise/status")
    assert resp.status_code in {401, 403, 404, 503}
