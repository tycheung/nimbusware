from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from agent_core.models import (  # noqa: E402
    EventType,
    ResearchBriefEmittedEvent,
    ResearchBriefEmittedPayload,
    RunCreatedEvent,
    RunCreatedPayload,
)
from nimbusware_store.memory import InMemoryEventStore  # noqa: E402
from nimbusware_api.app import app  # noqa: E402


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    store = InMemoryEventStore()
    with TestClient(app) as c:
        c.app.state.store = store
        c.app.state.orchestrator.store = store
        yield c


def _seed_run_with_brief(store: InMemoryEventStore) -> tuple[str, str]:
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
                config_snapshot_id="snap-test",
            ),
        ),
    )
    brief_id = "brief-test-1"
    store.append(
        ResearchBriefEmittedEvent(
            event_type=EventType.RESEARCH_BRIEF_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=ResearchBriefEmittedPayload(
                brief_kind="code",
                domain_tag="golf",
                summary="Fixture brief",
                artifact_id=brief_id,
                sources=[],
            ),
        ),
    )
    return str(run_id), brief_id


def test_get_run_research(client: TestClient) -> None:
    store = client.app.state.store
    run_id, brief_id = _seed_run_with_brief(store)
    r = client.get(f"/v1/runs/{run_id}/research")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["briefs"][0]["brief_id"] == brief_id
    assert body["briefs"][0]["status"] == "pending"


def test_approve_research_brief(client: TestClient) -> None:
    store = client.app.state.store
    run_id, brief_id = _seed_run_with_brief(store)
    r = client.post(f"/v1/runs/{run_id}/research/{brief_id}/approve", json={"notes": "looks good"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"
    body = client.get(f"/v1/runs/{run_id}/research").json()
    assert body["briefs"][0]["status"] == "approved"
