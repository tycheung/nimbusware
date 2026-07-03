from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from agent_core.models import (  # noqa: E402
    EventType,
    RunCreatedEvent,
    RunCreatedPayload,
    StagePassedEvent,
    StagePassedPayload,
)
from api.app import app  # noqa: E402
from store.memory import InMemoryEventStore  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    store = InMemoryEventStore()
    with TestClient(app) as c:
        c.app.state.store = store
        c.app.state.orchestrator.store = store
        yield c


def test_get_run_theater(client: TestClient) -> None:
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
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StagePassedPayload(stage_name="plan", duration_ms=10),
        ),
    )
    r = client.get(f"/v1/runs/{run_id}/theater")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
