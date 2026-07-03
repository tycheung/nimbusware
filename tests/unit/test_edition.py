from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app
from env.edition import (
    DEFAULT_EDITION,
    ENTERPRISE_EDITION,
    ENV_EDITION,
    edition,
    edition_manifest,
    enterprise_feature_enabled,
    enterprise_install_hints,
    is_enterprise,
    is_individual,
    normalize_edition,
    require_enterprise_feature,
)


def test_normalize_edition_defaults_individual() -> None:
    assert normalize_edition(None) == DEFAULT_EDITION
    assert normalize_edition("") == DEFAULT_EDITION
    assert normalize_edition("INDIVIDUAL") == DEFAULT_EDITION


def test_normalize_edition_strict_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="invalid NIMBUSWARE_EDITION"):
        normalize_edition("cloud", strict=True)


def test_edition_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_EDITION, raising=False)
    assert is_individual()
    assert not is_enterprise()
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    assert is_enterprise()
    assert edition() == ENTERPRISE_EDITION


def test_enterprise_feature_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, DEFAULT_EDITION)
    assert not enterprise_feature_enabled("iam")
    with pytest.raises(RuntimeError, match="Enterprise edition required"):
        require_enterprise_feature("iam")
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    assert enterprise_feature_enabled("iam")
    require_enterprise_feature("iam")


def test_edition_manifest_individual(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_EDITION, raising=False)
    manifest = edition_manifest()
    assert manifest["edition"] == DEFAULT_EDITION
    assert manifest["features"]["iam"]["status"] == "unavailable"


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_edition_manifest_enterprise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    manifest = edition_manifest()
    assert manifest["features"]["iam"]["status"] == "enabled"
    assert manifest["features"]["fleet_memory"]["status"] == "enabled"
    assert manifest["features"]["config_notify"]["status"] == "enabled"
    assert manifest["features"]["object_store_primary"]["status"] == "enabled"
    assert manifest["features"]["redis_fleet_worker"]["status"] == "enabled"
    assert manifest["features"]["fleet_ollama_sli"]["status"] == "enabled"
    assert manifest["features"]["enterprise_console"]["status"] == "enabled"


def test_enterprise_install_hints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_EDITION, raising=False)
    assert any("repo-scoped" in h for h in enterprise_install_hints())


def test_platform_edition_endpoint(client: TestClient) -> None:
    r = client.get("/v1/platform/edition")
    assert r.status_code == 200
    body = r.json()
    assert body["edition"] in {DEFAULT_EDITION, ENTERPRISE_EDITION}
    assert "features" in body


def test_enterprise_routes_404_on_individual(client: TestClient) -> None:
    if is_enterprise():
        pytest.skip("requires individual edition")
    r = client.get("/v1/enterprise/status")
    assert r.status_code == 404
    assert r.json()["code"] == "enterprise_edition_required"


def test_enterprise_routes_available_when_enterprise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "test-admin-secret")
    from api.app import app
    from iam.constants import API_KEY_HEADER

    with TestClient(app) as client:
        boot = client.post(
            "/v1/enterprise/iam/bootstrap",
            headers={"X-Nimbusware-Admin-Token": "test-admin-secret"},
        )
        assert boot.status_code == 200
        headers = {API_KEY_HEADER: boot.json()["api_key"]}
        r = client.get("/v1/enterprise/status", headers=headers)
        assert r.status_code == 200
        assert r.json()["lane"] == "D"
