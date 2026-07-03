from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.app import app
from store.memory import InMemoryEventStore


@pytest.fixture
def client() -> Iterator[TestClient]:
    store = InMemoryEventStore()
    with TestClient(app) as c:
        c.app.state.store = store
        c.app.state.orchestrator.store = store
        yield c


def test_competitive_summary_empty(client: TestClient) -> None:
    r = client.get("/v1/platform/analytics/competitive-summary")
    assert r.status_code == 200
    body = r.json()
    assert body["runs_scanned"] == 0
    assert body["snapshot"] is True
    assert "metrics" in body
