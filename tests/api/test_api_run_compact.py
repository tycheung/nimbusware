from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from agent_core.models import (  # noqa: E402
    EventType,
    RunCreatedEvent,
    RunCreatedPayload,
    StageStartedEvent,
    StageStartedPayload,
)
from agent_core.models.slice_handoff import SliceHandoffSummary  # noqa: E402
from nimbusware_api.app import app  # noqa: E402
from nimbusware_orchestrator.context_compaction import CompactionResult  # noqa: E402
from nimbusware_store.memory import InMemoryEventStore  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    store = InMemoryEventStore()
    with TestClient(app) as c:
        c.app.state.store = store
        c.app.state.orchestrator.store = store
        yield c


def _handoff(run_id: object, sid: str, summary: str) -> StageStartedEvent:
    handoff = SliceHandoffSummary(
        goal="campaign",
        progress=(f"{sid}: passed",),
        modified_files=(f"packages/{sid}.py",),
    )
    return StageStartedEvent(
        event_type=EventType.STAGE_STARTED,
        event_id=uuid4(),
        run_id=run_id,  # type: ignore[arg-type]
        occurred_at=datetime.now(timezone.utc),
        metadata={
            "slice_id": sid,
            "handoff_summary": summary,
            "slice_handoff": handoff.model_dump(mode="json"),
        },
        payload=StageStartedPayload(stage_name="slice.handoff", attempt=1),
    )


def _seed_handoffs(store: InMemoryEventStore) -> object:
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
    for i in range(4):
        store.append(
            _handoff(run_id, f"slice-{i}", ("x" * 500) + str(i)),
        )
    return run_id


@patch("nimbusware_api.routes.runs.compact.maybe_emit_compaction_event")
def test_post_compact_run(mock_compact, client: TestClient) -> None:
    mock_compact.return_value = CompactionResult(
        summary="## Goal\ncampaign",
        tokens_before=900,
        tokens_after=300,
        kept_event_seq_range=(1, 4),
        handoff=SliceHandoffSummary(goal="campaign"),
    )
    store = client.app.state.store
    run_id = _seed_handoffs(store)
    r = client.post(f"/v1/runs/{run_id}/compact")
    assert r.status_code == 200
    body = r.json()
    assert body["compacted"] is True
    assert body["tokens_before"] > body["tokens_after"]
    mock_compact.assert_called_once()


def test_post_compact_disabled(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_AGENT_COMPACT", "0")
    store = client.app.state.store
    run_id = _seed_handoffs(store)
    r = client.post(f"/v1/runs/{run_id}/compact")
    assert r.status_code == 403
