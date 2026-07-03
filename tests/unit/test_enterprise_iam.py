from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from agent_core.models import EventType, RunCreatedEvent, RunCreatedPayload
from api.app import app
from env.edition import DEFAULT_EDITION, ENTERPRISE_EDITION, ENV_EDITION
from iam.constants import API_KEY_HEADER, DEFAULT_TENANT_ID
from iam.context import resolve_store_tenant_id, set_auth_context
from iam.crypto import hash_api_key
from iam.store import InMemoryIamStore
from store.memory import InMemoryEventStore


def test_individual_skips_iam_enforcement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, DEFAULT_EDITION)
    with TestClient(app) as client:
        r = client.get("/v1/runs")
        assert r.status_code != 401 or r.json().get("code") != "api_key_required"


def test_api_key_hash_roundtrip() -> None:
    store = InMemoryIamStore()
    tenant = store.create_tenant(slug="acme", display_name="Acme")
    created = store.create_api_key(tenant_id=tenant.tenant_id, label="ops")
    ctx = store.verify_api_key(created.api_key)
    assert ctx is not None
    assert ctx.tenant_id == tenant.tenant_id
    assert ctx.tenant_slug == "acme"
    assert store.verify_api_key("nwb_invalid") is None


def test_event_store_tenant_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    iam = InMemoryIamStore()
    tenant_a = iam.create_tenant(slug="a", display_name="A")
    tenant_b = iam.create_tenant(slug="b", display_name="B")
    key_a = iam.create_api_key(tenant_id=tenant_a.tenant_id)
    key_b = iam.create_api_key(tenant_id=tenant_b.tenant_id)
    ctx_a = iam.verify_api_key(key_a.api_key)
    ctx_b = iam.verify_api_key(key_b.api_key)
    assert ctx_a is not None and ctx_b is not None

    store = InMemoryEventStore()
    run_a = uuid4()
    run_b = uuid4()

    set_auth_context(ctx_a)
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_a,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="wf-a",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    set_auth_context(ctx_b)
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_b,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="wf-b",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )

    set_auth_context(ctx_a)
    assert len(store.list_run_events(str(run_a))) == 1
    assert store.list_run_events(str(run_b)) == []

    set_auth_context(ctx_b)
    assert len(store.list_run_events(str(run_b))) == 1
    assert store.list_run_events(str(run_a)) == []


def test_individual_store_uses_default_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, DEFAULT_EDITION)
    assert resolve_store_tenant_id() == DEFAULT_TENANT_ID


def test_enterprise_bootstrap_and_me(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "test-admin-secret")
    from api.app import app

    with TestClient(app) as client:
        denied = client.get("/v1/enterprise/status")
        assert denied.status_code == 401
        assert denied.json()["code"] == "api_key_required"

        boot = client.post(
            "/v1/enterprise/iam/bootstrap",
            headers={"X-Nimbusware-Admin-Token": "test-admin-secret"},
        )
        assert boot.status_code == 200
        api_key = boot.json()["api_key"]
        headers = {API_KEY_HEADER: api_key}

        status = client.get("/v1/enterprise/status", headers=headers)
        assert status.status_code == 200
        assert status.json()["features"]["iam"]["status"] == "enabled"

        me = client.get("/v1/enterprise/iam/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["tenant_slug"] == "ops"
        assert "maker_admin" in me.json()["api_scopes"]


def test_enterprise_create_tenant_and_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "test-admin-secret")
    from api.app import app

    with TestClient(app) as client:
        boot = client.post(
            "/v1/enterprise/iam/bootstrap",
            headers={"X-Nimbusware-Admin-Token": "test-admin-secret"},
        )
        admin_headers = {API_KEY_HEADER: boot.json()["api_key"]}

        created = client.post(
            "/v1/enterprise/tenants",
            headers=admin_headers,
            json={"slug": "fleet", "display_name": "Fleet"},
        )
        assert created.status_code == 200
        tenant_id = created.json()["tenant_id"]

        key_resp = client.post(
            f"/v1/enterprise/tenants/{tenant_id}/api-keys",
            headers=admin_headers,
            json={"label": "worker", "role_taxonomy_keys": ["planner"]},
        )
        assert key_resp.status_code == 200
        assert key_resp.json()["api_key"].startswith("nwb_")

        list_resp = client.get("/v1/enterprise/tenants", headers=admin_headers)
        assert list_resp.status_code == 200
        slugs = {t["slug"] for t in list_resp.json()["tenants"]}
        assert {"default", "ops", "fleet"}.issubset(slugs)


def test_postgres_iam_store_verify(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    url = os.environ.get("NIMBUSWARE_DATABASE_URL")
    if not url:
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")
    from iam.store import PostgresIamStore

    store = PostgresIamStore(url)
    try:
        store.ensure_default_tenant()
    except Exception as exc:
        pytest.skip(f"postgres unavailable: {exc}")
    tenant = store.create_tenant(slug=f"iam-{uuid4().hex[:8]}", display_name="Test")
    created = store.create_api_key(tenant_id=tenant.tenant_id, label="itest")
    assert hash_api_key(created.api_key)  # smoke
    ctx = store.verify_api_key(created.api_key)
    assert ctx is not None
    assert ctx.tenant_id == tenant.tenant_id
