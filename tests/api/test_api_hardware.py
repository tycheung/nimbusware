from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from agent_core.models import EventType, RunCreatedEvent, RunCreatedPayload
from nimbusware_store.memory import InMemoryEventStore
from nimbusware_api.app import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    store = InMemoryEventStore()
    with TestClient(app) as c:
        c.app.state.store = store
        c.app.state.orchestrator.store = store
        yield c


def _seed_run(store: InMemoryEventStore):
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
    return run_id


def test_platform_hardware(client: TestClient) -> None:
    r = client.get("/v1/platform/hardware")
    assert r.status_code == 200
    body = r.json()
    assert "profile" in body
    assert "resource_governor" in body
    assert body["profile"]["tier"] in ("weak", "medium", "strong")


def test_platform_hardware_rescan(client: TestClient) -> None:
    r = client.post("/v1/platform/hardware/rescan", json={})
    assert r.status_code == 200
    assert "profile" in r.json()


def test_platform_hardware_rescan_emit_event(client: TestClient) -> None:
    store = client.app.state.store
    run_id = _seed_run(store)
    r = client.post(
        "/v1/platform/hardware/rescan",
        json={"emit_event": True, "run_id": str(run_id)},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("event_emitted") is True
    assert isinstance(body.get("store_seq"), int)
    rows = [row for row in store.list_all_event_rows() if row["run_id"] == run_id]
    assert any(row["event_type"] == EventType.HARDWARE_PROFILE_DETECTED.value for row in rows)


def test_platform_hardware_rescan_emit_requires_run_id(client: TestClient) -> None:
    r = client.post("/v1/platform/hardware/rescan", json={"emit_event": True})
    assert r.status_code == 422


def test_platform_hardware_fleet_individual_404(client: TestClient) -> None:
    r = client.get("/v1/platform/hardware/fleet")
    assert r.status_code == 404


def test_platform_pressure_history(client: TestClient) -> None:
    store = client.app.state.store
    run_id = _seed_run(store)
    client.post(
        "/v1/platform/hardware/rescan",
        json={"emit_event": True, "run_id": str(run_id)},
    )
    r = client.get("/v1/platform/analytics/pressure-history?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
    entry = body["entries"][0]
    assert "pressure_level" in entry
    assert "occurred_at" in entry
