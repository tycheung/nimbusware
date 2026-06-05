"""Event append and projection read path on Postgres."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from agent_core.models import (
    EventType,
    RunCreatedEvent,
    RunCreatedPayload,
    RunStartedEvent,
    RunStartedPayload,
)
from nimbusware_projections.builders.maker_progress import maker_progress_from_events
from nimbusware_store.postgres import PostgresEventStore

pytestmark = pytest.mark.integration


def _url() -> str:
    u = os.environ.get("NIMBUSWARE_DATABASE_URL")
    if not u:
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")
    return u


def test_maker_progress_projection_from_postgres_events() -> None:
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
    store.append(
        RunStartedEvent(
            event_type=EventType.RUN_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunStartedPayload(started_by="integration"),
        ),
    )
    rows = store.list_run_events(str(run_id))
    body = maker_progress_from_events(rows)
    assert body.get("current_headline")
    assert "plan_summary" in body
