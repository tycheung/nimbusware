from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from agent_core.models import (
    EventType,
    RunCreatedEvent,
    RunCreatedPayload,
    StagePassedEvent,
    StagePassedPayload,
)
from hermes_orchestrator.fleet_analytics import compare_tenant_metrics, tenant_run_metrics
from hermes_store.memory import InMemoryEventStore
from nimbusware_iam.constants import DEFAULT_TENANT_ID
from nimbusware_iam.context import reset_auth_context, set_auth_context
from nimbusware_iam.models import AuthContext


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


def test_tenant_run_metrics_counts_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EDITION", "enterprise")
    set_auth_context(_auth(DEFAULT_TENANT_ID))
    store = InMemoryEventStore()
    _seed_run(store, verdict="PASS")
    metrics = tenant_run_metrics(store, tenant_id=DEFAULT_TENANT_ID, run_limit=10)
    assert metrics["gate_metrics"]["slice_gates_passed"] >= 1


def test_compare_tenant_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EDITION", "enterprise")
    tid_b = uuid4()
    set_auth_context(_auth(DEFAULT_TENANT_ID))
    store = InMemoryEventStore()
    _seed_run(store, verdict="PASS")
    set_auth_context(_auth(tid_b))
    _seed_run(store, verdict="FAIL")
    out = compare_tenant_metrics(store, tenant_a=DEFAULT_TENANT_ID, tenant_b=tid_b, run_limit=20)
    assert "comparison" in out
