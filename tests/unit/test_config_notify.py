"""Config NOTIFY freshness."""

from __future__ import annotations

import pytest

from nimbusware_config.flags import config_notify_enabled
from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.notify import (
    NOTIFY_EVENT_TYPE,
    encode_notify_payload,
    get_config_notify_hub,
    parse_notify_payload,
)
from nimbusware_config.store import InMemoryConfigStore
from nimbusware_env.edition import DEFAULT_EDITION, ENTERPRISE_EDITION, ENV_EDITION


def test_parse_notify_payload_roundtrip() -> None:
    raw = encode_notify_payload(namespace="policy", document_key="model_routing", version=3)
    event = parse_notify_payload(raw)
    assert event is not None
    assert event.event_type == NOTIFY_EVENT_TYPE
    assert event.namespace == "policy"
    assert event.document_key == "model_routing"
    assert event.version == 3


def test_hub_invalidates_materializer_cache() -> None:
    store = InMemoryConfigStore()
    mat = ConfigMaterializer.__new__(ConfigMaterializer)
    mat._repo_root = __import__("pathlib").Path(".")
    mat._use_db = True
    mat._store = store
    mat._generation = 0
    mat._cache = {("policy", "model_routing"): {"old": True}}

    hub = get_config_notify_hub()
    hub.register(mat)
    hub.publish_local(namespace="policy", document_key="model_routing", version=2)

    assert ("policy", "model_routing") not in mat._cache
    assert mat.generation >= 1
    hub.unregister(mat)


def test_in_memory_upsert_publishes_when_notify_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_CONFIG_NOTIFY", "1")

    store = InMemoryConfigStore()
    mat = ConfigMaterializer.__new__(ConfigMaterializer)
    mat._repo_root = __import__("pathlib").Path(".")
    mat._use_db = True
    mat._store = store
    mat._generation = 0
    mat._cache = {("workflows", "default"): {"stages": []}}

    hub = get_config_notify_hub()
    hub.register(mat)
    store.upsert("workflows", "default", {"stages": [{"id": "s1"}]})
    assert ("workflows", "default") not in mat._cache
    hub.unregister(mat)


def test_config_notify_disabled_on_individual(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, DEFAULT_EDITION)
    monkeypatch.setenv("NIMBUSWARE_CONFIG_NOTIFY", "1")
    assert not config_notify_enabled()


def test_config_notify_enabled_on_enterprise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_CONFIG_NOTIFY", "1")
    assert config_notify_enabled()


def test_enterprise_config_notify_status_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_CONFIG_NOTIFY", "1")
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "test-admin-secret")
    from fastapi.testclient import TestClient

    from nimbusware_api.app import app
    from nimbusware_iam.constants import API_KEY_HEADER

    with TestClient(app) as client:
        boot = client.post(
            "/v1/enterprise/iam/bootstrap",
            headers={"X-Nimbusware-Admin-Token": "test-admin-secret"},
        )
        headers = {API_KEY_HEADER: boot.json()["api_key"]}
        r = client.get("/v1/enterprise/config-notify/status", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["event_type"] == NOTIFY_EVENT_TYPE
        assert body["enabled"] is True
