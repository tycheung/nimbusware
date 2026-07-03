from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest

from agent_core.models import EventType, RunCreatedEvent, RunCreatedPayload
from e2e.harness.stack import start_api_subprocess, stop_api_subprocess
from env import find_repo_root
from store.postgres import PostgresEventStore

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.e2e_journey,
    pytest.mark.e2e_stack,
    pytest.mark.integration,
]


@pytest.fixture
def postgres_url() -> str:
    url = os.environ.get("NIMBUSWARE_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")
    return url


def test_theater_stream_live_sse_from_api_stack(postgres_url: str) -> None:
    repo = find_repo_root()
    run_id = uuid4()
    store = PostgresEventStore(postgres_url)
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

    stack = start_api_subprocess(
        repo,
        env={
            "NIMBUSWARE_DATABASE_URL": postgres_url,
            "NIMBUSWARE_SKIP_PREFLIGHT": "1",
        },
    )
    try:
        with httpx.stream(
            "GET",
            f"{stack.base_url}/v1/runs/{run_id}/theater/stream",
            params={"poll_seconds": 0.25},
            timeout=30.0,
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            chunk = next(resp.iter_text())
            assert "event:" in chunk or "data:" in chunk
    finally:
        stop_api_subprocess(stack)
