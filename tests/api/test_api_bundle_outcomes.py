from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from agent_core.models import Verdict
from hermes_extensions.bundle_memory import (
    InMemoryBundleOutcomeStore,
    build_bundle_outcome_from_gate,
)
from hermes_store.memory import InMemoryEventStore
from nimbusware_api.app import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    store = InMemoryEventStore()
    with TestClient(app) as c:
        c.app.state.store = store
        c.app.state.orchestrator.store = store
        yield c


def test_bundle_outcomes_empty(client: TestClient) -> None:
    client.app.state.orchestrator._bundle_outcome_store = InMemoryBundleOutcomeStore()
    r = client.get("/v1/platform/analytics/bundle-outcomes")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert body["outcome_count"] == 0
    assert body["rows"] == []


def test_bundle_outcomes_seeded(client: TestClient) -> None:
    mem = InMemoryBundleOutcomeStore()
    mem.append(
        build_bundle_outcome_from_gate(
            run_id=uuid4(),
            bundle_id="auth-rbac",
            workflow_profile="default",
            project_tags=["auth"],
            integrator_score=0.9,
            verdict=Verdict.PASS,
        ),
    )
    mem.append(
        build_bundle_outcome_from_gate(
            run_id=uuid4(),
            bundle_id="auth-rbac",
            workflow_profile="default",
            project_tags=["auth"],
            integrator_score=0.4,
            verdict=Verdict.FAIL,
        ),
    )
    client.app.state.orchestrator._bundle_outcome_store = mem
    r = client.get("/v1/platform/analytics/bundle-outcomes")
    assert r.status_code == 200
    body = r.json()
    assert body["outcome_count"] == 2
    assert len(body["rows"]) == 1
    row = body["rows"][0]
    assert row["bundle_id"] == "auth-rbac"
    assert row["success_rate"] == 0.5
    assert row["avg_fit_on_pass"] == 0.9
    assert row["avg_fit_on_fail"] == 0.4
