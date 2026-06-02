from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from agent_core.models import (
    EventType,
    RunCreatedEvent,
    RunCreatedPayload,
)
from hermes_store.postgres import PostgresEventStore

pytestmark = pytest.mark.integration


def _url() -> str:
    u = os.environ.get("NIMBUSWARE_DATABASE_URL")
    if not u:
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")
    return u


def test_postgres_append_and_list_run_events() -> None:
    store = PostgresEventStore(_url())
    run_id = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    rows = store.list_run_events(str(run_id))
    assert len(rows) == 1
    assert rows[0]["event_type"] == "run.created"


def test_postgres_list_recent_run_ids_includes_new_run() -> None:
    store = PostgresEventStore(_url())
    run_id = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    ids = store.list_recent_run_ids(limit=50, workflow_profile="default")
    assert run_id in ids


def test_postgres_max_store_seq_for_run() -> None:
    store = PostgresEventStore(_url())
    run_id = uuid4()
    seq = store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    assert store.max_store_seq_for_run(str(run_id)) == seq


def test_postgres_get_run_head_returns_latest_event() -> None:
    store = PostgresEventStore(_url())
    run_id = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    head = store.get_run_head(str(run_id))
    assert head is not None
    assert head["event_type"] == "run.created"


def test_postgres_count_recent_runs_includes_new_run() -> None:
    store = PostgresEventStore(_url())
    run_id = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    ids = store.list_recent_run_ids(limit=100, workflow_profile="default")
    assert run_id in ids
    assert store.count_recent_runs(workflow_profile="default") >= 1
