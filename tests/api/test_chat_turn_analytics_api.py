from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from nimbusware_api.app import app
from nimbusware_maker.chat_store import InMemoryChatStore


@pytest.fixture
def client() -> Iterator[TestClient]:
    chat = InMemoryChatStore()
    with TestClient(app) as c:
        c.app.state.chat_store = chat
        yield c


def test_chat_turn_analytics_endpoint(client: TestClient) -> None:
    chat_store: InMemoryChatStore = client.app.state.chat_store
    project_id = uuid4()
    session = chat_store.create_session(project_id=project_id)
    chat_store.append_turn(session.session_id, role="user", text="fix bug")
    chat_store.append_turn(
        session.session_id,
        role="run_status",
        text="go",
        work_type="patch",
        work_type_source="classifier",
        run_id=uuid4(),
    )
    resp = client.get("/v1/platform/analytics/chat-turns?limit_sessions=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["turn_count"] >= 2
    assert body["classifier_start_count"] == 1
    journey = body.get("chat_journey_coverage") or {}
    assert journey.get("scenario_count", 0) >= 1
    assert "coverage_rate" in journey
    assert "meets_target" in journey
