from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from agent_core.models import (
    EventType,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    RunCreatedEvent,
    RunCreatedPayload,
    StitchAppliedEvent,
    StitchAppliedPayload,
    Verdict,
)
from api.app import app
from store.memory import InMemoryEventStore


@pytest.fixture
def client() -> Iterator[TestClient]:
    store = InMemoryEventStore()
    with TestClient(app) as c:
        c.app.state.store = store
        c.app.state.orchestrator.store = store
        yield c


def test_platform_stitch_outcomes_empty(client: TestClient) -> None:
    r = client.get("/v1/platform/analytics/stitch-outcomes")
    assert r.status_code == 200
    body = r.json()
    assert body["runs_with_stitch"] == 0
    assert body["sample_size"] == 0


def test_platform_stitch_outcomes_with_pass(client: TestClient) -> None:
    store = client.app.state.store
    run_id = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="micro_slice",
                policy_version="1",
                config_snapshot_id="snap",
            ),
        ),
    )
    store.append(
        StitchAppliedEvent(
            event_type=EventType.STITCH_APPLIED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StitchAppliedPayload(
                snapshot_ref="snap-1",
                files_added=["src/auth.py"],
                deps_added=[],
            ),
        ),
    )
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="integrator_gate",
                verdict=Verdict.PASS,
            ),
        ),
    )
    r = client.get("/v1/platform/analytics/stitch-outcomes")
    assert r.status_code == 200
    body = r.json()
    assert body["runs_with_stitch"] == 1
    assert body["transplant_pass"] == 1
