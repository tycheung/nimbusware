from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from agent_core.models import (
    EventType,
    RunCompletedEvent,
    RunCompletedPayload,
    RunCreatedEvent,
    RunCreatedPayload,
    RunEscalatedEvent,
    RunEscalatedPayload,
    RunStartedEvent,
    RunStartedPayload,
)
from iam.constants import DEFAULT_TENANT_ID
from store.memory import InMemoryEventStore


def _append_run_created(
    store: InMemoryEventStore,
    *,
    workflow_profile: str = "default",
    occurred_at: datetime | None = None,
    correlation_id: UUID | None = None,
) -> UUID:
    run_id = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=occurred_at or datetime.now(timezone.utc),
            correlation_id=correlation_id,
            payload=RunCreatedPayload(
                workflow_profile=workflow_profile,
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    return run_id


def _append_run_started(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        RunStartedEvent(
            event_type=EventType.RUN_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunStartedPayload(started_by="test"),
        ),
    )


def _append_run_completed(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        RunCompletedEvent(
            event_type=EventType.RUN_COMPLETED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCompletedPayload(summary="done"),
        ),
    )


def _append_run_escalated(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(actor_id="human-1", reason_code="needs_review"),
        ),
    )


def test_append_increments_store_seq_monotonically() -> None:
    store = InMemoryEventStore()
    rid = _append_run_created(store)
    s2 = store.append(
        RunStartedEvent(
            event_type=EventType.RUN_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=RunStartedPayload(started_by="test"),
        ),
    )
    assert s2 == 2
    assert store.list_run_events(str(rid))[0]["store_seq"] == 1
    assert store.list_run_events(str(rid))[1]["store_seq"] == 2


def test_list_run_events_ordered_and_isolated_by_run() -> None:
    store = InMemoryEventStore()
    rid_a = _append_run_created(store, workflow_profile="alpha")
    rid_b = _append_run_created(store, workflow_profile="beta")
    _append_run_started(store, rid_a)

    rows_a = store.list_run_events(str(rid_a))
    rows_b = store.list_run_events(str(rid_b))
    assert len(rows_a) == 2
    assert len(rows_b) == 1
    assert rows_a[0]["store_seq"] < rows_a[1]["store_seq"]
    assert rows_a[0]["event_type"] == "run.created"
    assert rows_a[1]["event_type"] == "run.started"


def test_list_run_events_many() -> None:
    store = InMemoryEventStore()
    rid_a = _append_run_created(store)
    rid_b = _append_run_created(store)
    missing = uuid4()
    _append_run_started(store, rid_a)

    batch = store.list_run_events_many([str(rid_a), str(rid_b), str(missing)])
    assert len(batch[str(rid_a)]) == 2
    assert len(batch[str(rid_b)]) == 1
    assert batch[str(missing)] == []
    assert batch[str(rid_b)][0]["run_id"] == rid_b


def test_get_run_head_and_max_store_seq() -> None:
    store = InMemoryEventStore()
    rid = _append_run_created(store)
    _append_run_started(store, rid)
    head = store.get_run_head(str(rid))
    assert head is not None
    assert head["event_type"] == "run.started"
    assert store.max_store_seq_for_run(str(rid)) == int(head["store_seq"])
    assert store.get_run_head(str(uuid4())) is None
    assert store.max_store_seq_for_run(str(uuid4())) is None


def test_find_run_id_for_run_created_correlation() -> None:
    store = InMemoryEventStore()
    corr = uuid4()
    rid = _append_run_created(store, correlation_id=corr)
    found = store.find_run_id_for_run_created_correlation(corr)
    assert found == rid
    assert store.find_run_id_for_run_created_correlation(uuid4()) is None


def test_list_all_event_rows_and_replay_validate() -> None:
    store = InMemoryEventStore()
    rid = _append_run_created(store)
    _append_run_started(store, rid)
    all_rows = store.list_all_event_rows()
    assert len(all_rows) == 2
    assert all_rows[0]["store_seq"] < all_rows[1]["store_seq"]
    events = store.replay_validate()
    assert len(events) == 2
    assert events[0].event_type == EventType.RUN_CREATED
    assert events[1].event_type == EventType.RUN_STARTED


def test_list_recent_run_ids_order_and_pagination() -> None:
    store = InMemoryEventStore()
    rid_old = _append_run_created(store, workflow_profile="old")
    rid_new = _append_run_created(store, workflow_profile="new")
    _append_run_started(store, rid_old)

    newest = store.list_recent_run_ids(limit=10)
    assert newest[0] == rid_old
    assert newest[1] == rid_new

    oldest = store.list_recent_run_ids(order="oldest_first")
    assert oldest[0] == rid_new
    assert oldest[1] == rid_old

    page = store.list_recent_run_ids(limit=1, offset=1)
    assert len(page) == 1
    assert page[0] == rid_new


def test_list_recent_run_ids_workflow_profile_filters() -> None:
    store = InMemoryEventStore()
    _append_run_created(store, workflow_profile="agent_evaluator_on")
    rid_default = _append_run_created(store, workflow_profile="default")

    exact = store.list_recent_run_ids(workflow_profile="default")
    assert exact == [rid_default]

    prefix = store.list_recent_run_ids(workflow_profile_prefix="agent_")
    assert len(prefix) == 1

    exact_beats_prefix = store.list_recent_run_ids(
        workflow_profile="default",
        workflow_profile_prefix="agent_",
    )
    assert exact_beats_prefix == [rid_default]


def test_list_recent_run_ids_created_window_and_escalation() -> None:
    store = InMemoryEventStore()
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=1)
    t2 = t0 + timedelta(hours=2)
    rid_early = _append_run_created(store, occurred_at=t0)
    rid_late = _append_run_created(store, occurred_at=t2)
    _append_run_escalated(store, rid_late)

    in_window = store.list_recent_run_ids(created_after=t1, created_before=t2)
    assert in_window == [rid_late]

    escalated = store.list_recent_run_ids(has_escalation=True)
    assert escalated == [rid_late]

    no_esc = store.list_recent_run_ids(has_escalation=False)
    assert no_esc == [rid_early]


def test_list_recent_run_ids_list_status() -> None:
    store = InMemoryEventStore()
    rid_created = _append_run_created(store)
    rid_running = _append_run_created(store)
    _append_run_started(store, rid_running)
    rid_terminal = _append_run_created(store)
    _append_run_completed(store, rid_terminal)

    assert store.list_recent_run_ids(list_status="created") == [rid_created]
    assert rid_running in store.list_recent_run_ids(list_status="running")
    assert store.list_recent_run_ids(list_status="terminal") == [rid_terminal]


def test_count_recent_runs_matches_list_filters() -> None:
    store = InMemoryEventStore()
    _append_run_created(store, workflow_profile="alpha")
    _append_run_created(store, workflow_profile="beta")
    assert store.count_recent_runs() == 2
    assert store.count_recent_runs(workflow_profile_prefix="alpha") == 1


def test_list_recent_run_rows_cursor() -> None:
    store = InMemoryEventStore()
    _append_run_created(store)
    _append_run_created(store)
    _append_run_created(store)

    ordered = store.list_recent_run_ids(limit=10)
    head_run, head_seq = ordered[0], store.max_store_seq_for_run(str(ordered[0]))
    assert head_seq is not None

    page, has_more = store.list_recent_run_rows_cursor(
        limit=1,
        cursor_after_seq=head_seq,
        cursor_after_run_id=head_run,
    )
    assert len(page) == 1
    assert has_more is True
    assert page[0][0] == ordered[1]

    last_run = ordered[-1]
    last_seq = store.max_store_seq_for_run(str(last_run))
    assert last_seq is not None
    tail, has_more_tail = store.list_recent_run_rows_cursor(
        limit=5,
        cursor_after_seq=last_seq,
        cursor_after_run_id=last_run,
    )
    assert tail == []
    assert has_more_tail is False


def test_list_recent_run_rows_cursor_oldest_first() -> None:
    store = InMemoryEventStore()
    _append_run_created(store)
    _append_run_created(store)
    _append_run_created(store)
    ordered = store.list_recent_run_ids(order="oldest_first")
    first_run = ordered[0]
    first_seq = store.max_store_seq_for_run(str(first_run))
    assert first_seq is not None
    page, has_more = store.list_recent_run_rows_cursor(
        limit=1,
        cursor_after_seq=first_seq,
        cursor_after_run_id=first_run,
        order="oldest_first",
    )
    assert page[0][0] == ordered[1]
    assert has_more is True


def test_append_rejects_unregistered_event_type(monkeypatch: pytest.MonkeyPatch) -> None:
    from agent_core.models import serialize_event_persistent

    store = InMemoryEventStore()
    event = RunCreatedEvent(
        event_type=EventType.RUN_CREATED,
        event_id=uuid4(),
        run_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        payload=RunCreatedPayload(
            workflow_profile="default",
            policy_version="1",
            config_snapshot_id="snap",
        ),
    )

    def _bad_serialize(ev: object) -> dict[str, object]:
        full = serialize_event_persistent(ev)  # type: ignore[arg-type]
        full["event_type"] = "totally.invalid.type"
        return full

    monkeypatch.setattr("agent_core.models.serialize_event_persistent", _bad_serialize)
    with pytest.raises(ValueError, match="not in EventType"):
        store.append(event)


def test_private_helpers_cover_edge_branches() -> None:
    store = InMemoryEventStore()
    assert store._replay_list_status(uuid4()) == "unknown"  # noqa: SLF001

    rid = uuid4()
    store._rows.append(  # noqa: SLF001
        {
            "store_seq": 1,
            "tenant_id": DEFAULT_TENANT_ID,
            "event_id": uuid4(),
            "run_id": rid,
            "stage_id": None,
            "task_id": None,
            "event_type": "run.started",
            "event_version": 1,
            "occurred_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "actor_role": None,
            "model_id": None,
            "correlation_id": None,
            "causation_id": None,
            "payload": {},
            "metadata": {},
        },
    )
    assert store._workflow_profile_for_run(rid) is None  # noqa: SLF001

    rid_naive = uuid4()
    store._rows.append(  # noqa: SLF001
        {
            "store_seq": 2,
            "tenant_id": DEFAULT_TENANT_ID,
            "event_id": uuid4(),
            "run_id": rid_naive,
            "stage_id": None,
            "task_id": None,
            "event_type": "run.created",
            "event_version": 1,
            "occurred_at": datetime(2026, 2, 1, 8, 0),
            "actor_role": None,
            "model_id": None,
            "correlation_id": None,
            "causation_id": None,
            "payload": {"workflow_profile": "default"},
            "metadata": {},
        },
    )
    created_at = store._run_created_at(rid_naive)  # noqa: SLF001
    assert created_at is not None
    assert created_at.tzinfo is not None

    rid_esc = _append_run_created(store)
    _append_run_escalated(store, rid_esc)
    assert store._replay_list_status(rid_esc) == "running"  # noqa: SLF001


def test_invalid_order_defaults_to_newest_first() -> None:
    store = InMemoryEventStore()
    rid_a = _append_run_created(store)
    rid_b = _append_run_created(store)
    _append_run_started(store, rid_a)

    ordered = store.list_recent_run_ids(order="not-a-valid-order")
    assert ordered[0] == rid_a

    head_seq = store.max_store_seq_for_run(str(rid_a))
    assert head_seq is not None
    page, _ = store.list_recent_run_rows_cursor(
        limit=5,
        cursor_after_seq=head_seq,
        cursor_after_run_id=rid_a,
        order="bogus-order",
    )
    assert page[0][0] == rid_b
