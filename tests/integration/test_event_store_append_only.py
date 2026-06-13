from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest

from agent_core.models import EventType, RunCreatedEvent, RunCreatedPayload
from nimbusware_store.postgres import PostgresEventStore

pytestmark = pytest.mark.integration


def _url() -> str:
    u = os.environ.get("NIMBUSWARE_DATABASE_URL")
    if not u:
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")
    return u


def test_event_store_rejects_update_and_delete() -> None:
    store = PostgresEventStore(_url())
    run_id = uuid4()
    event_id = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=event_id,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )

    with psycopg.connect(_url()) as conn:
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
                cur.execute(
                    "UPDATE event_store SET event_type = %s WHERE event_id = %s",
                    ("run.hacked", event_id),
                )
            conn.rollback()
            with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
                cur.execute("DELETE FROM event_store WHERE event_id = %s", (event_id,))
            conn.rollback()

    rows = store.list_run_events(str(run_id))
    assert len(rows) == 1
    assert rows[0]["event_type"] == "run.created"
