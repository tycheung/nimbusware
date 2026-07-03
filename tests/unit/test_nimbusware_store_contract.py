from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from agent_core.models import (
    EventType,
    RunCreatedEvent,
    RunCreatedPayload,
    serialize_event_persistent,
)
from store.allowed_types import allowed_event_type_values, assert_event_type_registered
from store.memory import InMemoryEventStore
from store.protocol import (
    EventStore,
    event_row_from_serialized,
    serialized_event_from_row,
)


def test_allowed_event_type_values_matches_event_type_enum() -> None:
    from_code = set(allowed_event_type_values())
    from_enum = {e.value for e in EventType}
    assert from_code == from_enum
    assert tuple(sorted(from_code)) == allowed_event_type_values()


def test_assert_event_type_registered_accepts_known_type() -> None:
    assert_event_type_registered(EventType.RUN_CREATED.value)


def test_assert_event_type_registered_rejects_unknown_type() -> None:
    with pytest.raises(ValueError, match="not in EventType"):
        assert_event_type_registered("not.a.real.event")


def test_event_row_from_serialized_splits_columns() -> None:
    event = RunCreatedEvent(
        event_type=EventType.RUN_CREATED,
        event_id=uuid4(),
        run_id=uuid4(),
        occurred_at=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        correlation_id=uuid4(),
        payload=RunCreatedPayload(
            workflow_profile="default",
            policy_version="1",
            config_snapshot_id="snap-1",
        ),
        metadata={"source": "test"},
    )
    full = serialize_event_persistent(event)
    row = event_row_from_serialized(full)
    assert row["event_id"] == str(event.event_id)
    assert row["run_id"] == str(event.run_id)
    assert row["event_type"] == "run.created"
    assert row["event_version"] == 1
    assert row["correlation_id"] == str(event.correlation_id)
    assert row["payload"]["workflow_profile"] == "default"
    assert row["metadata"] == {"source": "test"}


def test_serialized_event_from_row_minimal_shape() -> None:
    eid = uuid4()
    rid = uuid4()
    row = {
        "event_id": eid,
        "run_id": rid,
        "occurred_at": "2026-01-15T12:00:00Z",
        "event_type": "run.created",
        "payload": {"workflow_profile": "default"},
    }
    out = serialized_event_from_row(row)
    assert out["event_id"] == str(eid)
    assert out["run_id"] == str(rid)
    assert out["occurred_at"] == "2026-01-15T12:00:00Z"
    assert out["event_type"] == "run.created"
    assert out["event_version"] == 1
    assert out["metadata"] == {}


def test_serialized_event_from_row_datetime_converts_to_utc_z() -> None:
    dt = datetime(2026, 6, 1, 8, 30, tzinfo=timezone.utc)
    row = {
        "event_id": uuid4(),
        "run_id": uuid4(),
        "occurred_at": dt,
        "event_type": "run.created",
        "payload": {},
    }
    out = serialized_event_from_row(row)
    assert out["occurred_at"] == "2026-06-01T08:30:00Z"


def test_serialized_event_from_row_includes_optional_envelope_fields() -> None:
    stage_id = uuid4()
    task_id = uuid4()
    correlation_id = uuid4()
    causation_id = uuid4()
    actor_role = uuid4()
    row = {
        "event_id": uuid4(),
        "run_id": uuid4(),
        "stage_id": stage_id,
        "task_id": task_id,
        "occurred_at": datetime.now(timezone.utc),
        "event_type": "run.started",
        "event_version": 2,
        "actor_role": actor_role,
        "model_id": "gpt-test",
        "correlation_id": correlation_id,
        "causation_id": causation_id,
        "payload": {"started_by": "tester"},
        "metadata": {"k": "v"},
    }
    out = serialized_event_from_row(row)
    assert out["stage_id"] == str(stage_id)
    assert out["task_id"] == str(task_id)
    assert out["actor_role"] == str(actor_role)
    assert out["model_id"] == "gpt-test"
    assert out["correlation_id"] == str(correlation_id)
    assert out["causation_id"] == str(causation_id)
    assert out["event_version"] == 2


def test_event_row_and_serialized_round_trip() -> None:
    event = RunCreatedEvent(
        event_type=EventType.RUN_CREATED,
        event_id=uuid4(),
        run_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        payload=RunCreatedPayload(
            workflow_profile="agent_evaluator_on",
            policy_version="1",
            config_snapshot_id="snap-2",
        ),
    )
    full = serialize_event_persistent(event)
    row = event_row_from_serialized(full)
    db_row = {
        "event_id": UUID(str(row["event_id"])),
        "run_id": UUID(str(row["run_id"])),
        "occurred_at": datetime.fromisoformat(
            str(row["occurred_at"]).replace("Z", "+00:00"),
        ),
        "event_type": row["event_type"],
        "event_version": row["event_version"],
        "payload": row["payload"],
        "metadata": row["metadata"],
    }
    restored = serialized_event_from_row(db_row)
    assert restored["event_type"] == full["event_type"]
    assert restored["run_id"] == full["run_id"]
    assert restored["payload"] == full["payload"]


def test_in_memory_event_store_satisfies_event_store_protocol() -> None:
    store = InMemoryEventStore()
    assert isinstance(store, EventStore)


def test_postgres_run_list_status_fragments_without_status() -> None:
    from store.postgres import _run_list_status_fragments

    join, filt, extra = _run_list_status_fragments(None)
    assert join == ""
    assert filt == ""
    assert extra == {}


def test_postgres_run_list_status_fragments_with_status() -> None:
    from store.postgres import _run_list_status_fragments

    join, filt, extra = _run_list_status_fragments("running")
    assert "run_list_status" in join
    assert "lst" in filt
    assert extra == {"lst": "running"}
