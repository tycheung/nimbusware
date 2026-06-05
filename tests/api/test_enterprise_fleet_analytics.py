from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from agent_core.models import (
    EventType,
    RunCreatedEvent,
    RunCreatedPayload,
    StagePassedEvent,
    StagePassedPayload,
)
from nimbusware_api.app import app
from nimbusware_env.edition import ENTERPRISE_EDITION, ENV_EDITION
from nimbusware_iam.constants import API_KEY_HEADER, DEFAULT_TENANT_ID
from nimbusware_iam.context import reset_auth_context, set_auth_context
from nimbusware_iam.models import AuthContext
from nimbusware_iam.store import InMemoryIamStore
from nimbusware_store.memory import InMemoryEventStore


def _auth(tenant_id) -> AuthContext:
    return AuthContext(
        tenant_id=tenant_id,
        tenant_slug="t",
        key_id=uuid4(),
        role_taxonomy_keys=(),
        api_scopes=("maker_admin",),
    )


def _seed_run(store: InMemoryEventStore, *, verdict: str) -> None:
    run_id = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=RunCreatedPayload(
                workflow_profile="micro_slice",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"slice_gate_verdict": verdict},
            payload=StagePassedPayload(stage_name="slice.gate", duration_ms=0),
        ),
    )


@pytest.fixture(autouse=True)
def _reset_tenant_ctx() -> None:
    yield
    reset_auth_context()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    store = InMemoryEventStore()
    iam = InMemoryIamStore()
    key = iam.create_api_key(tenant_id=DEFAULT_TENANT_ID, api_scopes=["maker_admin"])
    with TestClient(app) as c:
        c.app.state.store = store
        c.app.state.orchestrator.store = store
        c.app.state.iam_store = iam
        c.test_api_key = key.api_key  # type: ignore[attr-defined]
        yield c


def test_fleet_analytics_compare_individual_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, "individual")
    store = InMemoryEventStore()
    iam = InMemoryIamStore()
    key = iam.create_api_key(tenant_id=DEFAULT_TENANT_ID, api_scopes=["maker_admin"])
    tid_b = uuid4()
    with TestClient(app) as client:
        client.app.state.store = store
        client.app.state.iam_store = iam
        r = client.get(
            "/v1/enterprise/fleet/analytics/compare",
            params={"tenant_a": str(DEFAULT_TENANT_ID), "tenant_b": str(tid_b)},
            headers={API_KEY_HEADER: key.api_key},
        )
        assert r.status_code == 404


def test_fleet_analytics_compare_route(client: TestClient) -> None:
    tid_b = uuid4()
    set_auth_context(_auth(DEFAULT_TENANT_ID))
    _seed_run(client.app.state.store, verdict="PASS")
    set_auth_context(_auth(tid_b))
    _seed_run(client.app.state.store, verdict="FAIL")
    r = client.get(
        "/v1/enterprise/fleet/analytics/compare",
        params={"tenant_a": str(DEFAULT_TENANT_ID), "tenant_b": str(tid_b)},
        headers={API_KEY_HEADER: client.test_api_key},
    )
    assert r.status_code == 200
    body = r.json()
    assert "tenant_a" in body
    assert "tenant_b" in body
    assert "comparison" in body
    assert body["tenant_a"]["gate_metrics"]["slice_gates_passed"] >= 1
