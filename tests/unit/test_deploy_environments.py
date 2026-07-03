from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app
from maker.deploy.target_enforcement import (
    DEFAULT_DEPLOY_ENVIRONMENT,
    normalize_deploy_environment,
    resolve_deploy_environment,
)
from maker.stack_manifest import parse_stack_manifest


def test_normalize_deploy_environment() -> None:
    assert normalize_deploy_environment("staging") == "staging"
    with pytest.raises(ValueError):
        normalize_deploy_environment("qa")


def test_resolve_deploy_environment_priority() -> None:
    assert resolve_deploy_environment(explicit="prod") == "prod"
    assert (
        resolve_deploy_environment(
            credentials={"deploy_environment": "staging"},
            manifest_raw={"deploy_environment": "prod"},
        )
        == "staging"
    )
    assert resolve_deploy_environment(manifest_raw={"deploy_environment": "prod"}) == "prod"
    assert resolve_deploy_environment() == DEFAULT_DEPLOY_ENVIRONMENT


def test_stack_manifest_deploy_environment() -> None:
    manifest = parse_stack_manifest(
        {
            "surfaces": ["api"],
            "stacks": {"api": "fastapi_python"},
            "deploy_environment": "staging",
        },
    )
    assert manifest.deploy_environment == "staging"


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_deploy_environments_catalog(client: TestClient) -> None:
    resp = client.get("/v1/platform/deploy/environments")
    assert resp.status_code == 200
    body = resp.json()
    assert body["default"] == "dev"
    assert set(body["environments"]) == {"dev", "staging", "prod"}
