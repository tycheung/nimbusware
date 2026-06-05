from __future__ import annotations

import os
import tarfile
from collections.abc import Iterator
from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from agent_core.models import (  # noqa: E402
    EventType,
    RunCreatedEvent,
    RunCreatedPayload,
    StagePassedEvent,
    StagePassedPayload,
)
from nimbusware_api.app import app  # noqa: E402
from nimbusware_api.read_models.run_theater import build_run_theater_messages
from nimbusware_orchestrator.audit_export import build_audit_bundle_bytes
from nimbusware_projections.exporters.theater_transcript import format_theater_transcript_md
from nimbusware_store.memory import InMemoryEventStore  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    store = InMemoryEventStore()
    with TestClient(app) as c:
        c.app.state.store = store
        c.app.state.orchestrator.store = store
        yield c


def _seed_run(store: InMemoryEventStore) -> object:
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
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StagePassedPayload(stage_name="plan", duration_ms=10),
        ),
    )
    return run_id


def test_get_run_theater_export_markdown(client: TestClient) -> None:
    store = client.app.state.store
    run_id = _seed_run(store)
    r = client.get(f"/v1/runs/{run_id}/theater/export")
    assert r.status_code == 200
    assert "text/markdown" in r.headers.get("content-type", "")
    assert "# Run theater transcript" in r.text
    assert "Planner" in r.text or "Stage passed" in r.text


def test_audit_bundle_includes_theater_transcript() -> None:
    run_id = str(uuid4())
    events = [{"event_type": "run.created", "event_id": str(uuid4())}]
    md = format_theater_transcript_md(run_id=run_id, messages=[])
    bundle = build_audit_bundle_bytes(
        run_id=run_id,
        events=events,
        policy_snapshot={"policy_version": "1"},
        theater_transcript_md=md,
    )
    with tarfile.open(fileobj=BytesIO(bundle), mode="r:gz") as tar:
        names = {m.name for m in tar.getmembers()}
    assert "theater_transcript.md" in names


def test_audit_export_endpoint_includes_theater_file(client: TestClient) -> None:
    store = client.app.state.store
    run_id = _seed_run(store)
    r = client.get(f"/v1/runs/{run_id}/audit-export")
    assert r.status_code == 200
    rows = store.list_run_events(str(run_id))
    expected = format_theater_transcript_md(
        run_id=str(run_id),
        messages=build_run_theater_messages(rows),
    )
    with tarfile.open(fileobj=BytesIO(r.content), mode="r:gz") as tar:
        names = {m.name for m in tar.getmembers()}
        assert "theater_transcript.md" in names
        member = tar.getmember("theater_transcript.md")
        extracted = tar.extractfile(member)
        assert extracted is not None
        assert extracted.read().decode("utf-8") == expected
