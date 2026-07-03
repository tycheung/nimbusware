from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import EventType, RunCreatedEvent, RunCreatedPayload
from projections.run_summary import build_run_summary
from store.memory import InMemoryEventStore
from store.protocol import serialized_event_from_row


def test_build_run_summary_created() -> None:
    store = InMemoryEventStore()
    rid = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id="snap",
            ),
        ),
    )
    rows = store.list_run_events(str(rid))
    s = build_run_summary(rows)
    assert s["status"] == "created"
    assert s["workflow_profile"] == "default"
    assert s["event_count"] == 1


def test_build_run_summary_empty() -> None:
    assert build_run_summary([])["status"] == "unknown"


def test_serialized_round_trip_row_shape() -> None:
    store = InMemoryEventStore()
    rid = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id="snap",
            ),
        ),
    )
    row = store.list_run_events(str(rid))[0]
    d = serialized_event_from_row(row)
    assert d["event_type"] == "run.created"
