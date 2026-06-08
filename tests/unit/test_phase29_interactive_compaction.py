from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
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
from nimbusware_maker.workspace import project_metadata_block  # noqa: E402
from nimbusware_orchestrator.context_artifacts import (  # noqa: E402
    clear_context_artifacts_memory,
    create_context_artifact,
    list_context_artifacts,
)
from nimbusware_orchestrator.context_compaction import (  # noqa: E402
    compact_campaign_context,
    emit_compaction_revert_event,
    reverted_compaction_ids,
)
from nimbusware_projections.builders.run_theater import build_run_theater_messages  # noqa: E402
from nimbusware_store.memory import InMemoryEventStore  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    store = InMemoryEventStore()
    with TestClient(app) as c:
        c.app.state.store = store
        c.app.state.orchestrator.store = store
        yield c


def _handoff_event(sid: str, *, seq: int, summary: str) -> dict:
    handoff = SliceHandoffSummary(
        goal="campaign",
        progress=(f"{sid}: passed",),
        modified_files=(f"packages/{sid}.py",),
    )
    return {
        "seq": seq,
        "store_seq": seq,
        "payload": {"stage_name": "slice.handoff"},
        "metadata": {
            "slice_id": sid,
            "handoff_summary": summary,
            "slice_handoff": handoff.model_dump(),
        },
    }


def _compacted_event(compaction_id: str, *, seq: int, summary: str) -> dict:
    handoff = SliceHandoffSummary(goal="merged", progress=("slice-1: passed",))
    return {
        "seq": seq,
        "store_seq": seq,
        "event_type": EventType.STAGE_STARTED.value,
        "payload": {"stage_name": "campaign.context.compacted"},
        "metadata": {
            "compaction_id": compaction_id,
            "summary": summary,
            "slice_handoff": handoff.model_dump(),
            "tokens_before": 1000,
            "tokens_after": 400,
        },
    }


def test_reverted_compaction_skipped_as_prior() -> None:
    cid = str(uuid4())
    prior_summary = "PRIOR_COMPACTED_SUMMARY"
    events = [
        _compacted_event(cid, seq=5, summary=prior_summary),
        _handoff_event("slice-1", seq=6, summary="a" * 500),
        _handoff_event("slice-2", seq=7, summary="b" * 500),
        _handoff_event("slice-3", seq=8, summary="c" * 500),
        _handoff_event("slice-4", seq=9, summary="d" * 500),
        {
            "seq": 10,
            "store_seq": 10,
            "payload": {"stage_name": "campaign.context.compaction.reverted"},
            "metadata": {
                "compaction_id": cid,
                "reverted_by": "operator",
                "reason": "too aggressive",
            },
        },
    ]
    assert cid in reverted_compaction_ids(events)
    result = compact_campaign_context(events, keep_recent_tokens=150, reserve_tokens=50)
    assert result is not None
    assert prior_summary not in result.summary


def test_emit_compaction_revert_event() -> None:
    store = InMemoryEventStore()
    run_id = uuid4()
    cid = str(uuid4())
    emit_compaction_revert_event(
        store,
        run_id=run_id,
        compaction_id=cid,
        reverted_by="maker",
        reason="undo",
    )
    rows = store.list_run_events(str(run_id))
    assert len(rows) == 1
    row = rows[0]
    assert (row.get("payload") or {}).get("stage_name") == "campaign.context.compaction.reverted"
    meta = row.get("metadata") or {}
    assert meta.get("compaction_id") == cid
    assert meta.get("reverted_by") == "maker"
    assert meta.get("reason") == "undo"


def test_theater_renders_compaction_reverted() -> None:
    run_id = uuid4()
    row = StageStartedEvent(
        event_type=EventType.STAGE_STARTED,
        event_id=uuid4(),
        run_id=run_id,
        occurred_at=datetime.now(timezone.utc),
        metadata={
            "compaction_id": str(uuid4()),
            "reverted_by": "operator",
            "reason": "restore detail",
        },
        payload=StageStartedPayload(stage_name="campaign.context.compaction.reverted", attempt=1),
    ).model_dump(mode="json")
    row["store_seq"] = 3
    msgs = build_run_theater_messages([row])
    assert msgs
    assert "reverted" in (msgs[0].get("headline") or "").lower()
    assert msgs[0].get("data_testid") == "theater-context-compaction-reverted"


def test_post_compaction_revert_api(client: TestClient) -> None:
    store = client.app.state.store
    run_id = uuid4()
    cid = str(uuid4())
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
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"compaction_id": cid, "summary": "merged"},
            payload=StageStartedPayload(stage_name="campaign.context.compacted", attempt=1),
        ),
    )
    r = client.post(
        f"/v1/runs/{run_id}/compactions/{cid}/revert",
        json={"reverted_by": "operator", "reason": "test"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["reverted"] is True
    assert body["compaction_id"] == cid


def test_scoped_compact_last_n() -> None:
    events = [
        _handoff_event(f"slice-{i}", seq=i + 1, summary=("x" * 500) + str(i)) for i in range(8)
    ]
    all_result = compact_campaign_context(
        events, keep_recent_tokens=150, reserve_tokens=50, scope="all"
    )
    last4 = compact_campaign_context(
        events,
        keep_recent_tokens=150,
        reserve_tokens=50,
        scope="last_n",
        scope_n=4,
    )
    assert all_result is not None
    assert last4 is not None
    assert last4.merged_handoff_count <= all_result.merged_handoff_count


def test_post_compact_scoped_body(client: TestClient) -> None:
    store = client.app.state.store
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
    for i in range(5):
        store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata={
                    "slice_id": f"slice-{i}",
                    "handoff_summary": ("h" * 500) + str(i),
                    "slice_handoff": SliceHandoffSummary(goal="g").model_dump(mode="json"),
                },
                payload=StageStartedPayload(stage_name="slice.handoff", attempt=1),
            ),
        )
    r = client.post(f"/v1/runs/{run_id}/compact", json={"scope": "last_n", "n": 4})
    assert r.status_code == 200
    empty = client.post(f"/v1/runs/{run_id}/compact")
    assert empty.status_code == 200


@pytest.fixture
def project_client(tmp_path: Path) -> Iterator[TestClient]:
    clear_context_artifacts_memory()
    store = InMemoryEventStore()
    with TestClient(app) as c:
        c.app.state.store = store
        c.app.state.orchestrator.store = store
        c.app.state.project_store._projects.clear()  # type: ignore[attr-defined]
        ws = tmp_path / "ws"
        ws.mkdir()
        created = c.app.state.project_store.create(
            name="phase29",
            workspace_path=str(ws),
            template="attach",
        )
        c._test_project_id = str(created.project_id)  # type: ignore[attr-defined]
        yield c
    clear_context_artifacts_memory()


def test_context_artifact_create_and_list(project_client: TestClient) -> None:
    pid = project_client._test_project_id  # type: ignore[attr-defined]
    created = create_context_artifact(
        project_id=pid,
        title="API contract",
        content="Use OpenAPI 3.1",
        kind="constraint",
    )
    rows = list_context_artifacts(pid)
    assert len(rows) == 1
    assert rows[0].artifact_id == created.artifact_id
    r = project_client.post(
        f"/v1/projects/{pid}/context-artifacts",
        json={"title": "Style", "content": "Black formatting", "kind": "note"},
    )
    assert r.status_code == 200
    listed = project_client.get(f"/v1/projects/{pid}/context-artifacts")
    assert listed.status_code == 200
    body = listed.json()
    assert body["count"] >= 2


def test_insert_context_artifact_into_run(project_client: TestClient) -> None:
    pid = project_client._test_project_id  # type: ignore[attr-defined]
    artifact = create_context_artifact(
        project_id=pid,
        title="Run note",
        content="Keep migrations reversible",
    )
    from uuid import UUID

    run_id = uuid4()
    project = project_client.app.state.project_store.get(UUID(pid))
    assert project is not None
    store = project_client.app.state.store
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "project": project_metadata_block(
                    project_id=project.project_id,
                    name=project.name,
                    workspace_path=Path(project.workspace_path),
                    template=project.template,
                ),
            },
            payload=RunCreatedPayload(
                workflow_profile="micro_slice",
                policy_version="1",
                config_snapshot_id="snap",
            ),
        ),
    )
    r = project_client.post(
        f"/v1/runs/{run_id}/context-artifacts/{artifact.artifact_id}/insert",
    )
    assert r.status_code == 200
    rows = store.list_run_events(str(run_id))
    inserted = [
        row
        for row in rows
        if (row.get("payload") or {}).get("stage_name") == "campaign.context.artifact.inserted"
    ]
    assert len(inserted) == 1
