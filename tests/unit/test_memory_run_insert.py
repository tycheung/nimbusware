from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from agent_core.models import (  # noqa: E402
    EventType,
    RunCreatedEvent,
    RunCreatedPayload,
)
from nimbusware_api.app import app  # noqa: E402
from nimbusware_maker.workspace import project_metadata_block  # noqa: E402
from nimbusware_memory.models import MemoryChunkRecord  # noqa: E402
from nimbusware_memory.repo_scope import repo_scope_hash  # noqa: E402
from nimbusware_memory.store_memory import InMemoryMemoryChunkStore  # noqa: E402
from nimbusware_store.memory import InMemoryEventStore  # noqa: E402


@pytest.fixture
def memory_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    store = InMemoryEventStore()
    chunk_store = InMemoryMemoryChunkStore()
    monkeypatch.setattr(
        "nimbusware_api.routes.runs.memory_insert.build_memory_chunk_store",
        lambda **_: chunk_store,
    )
    with TestClient(app) as c:
        c.app.state.store = store
        c.app.state.orchestrator.store = store
        c.app.state.project_store._projects.clear()  # type: ignore[attr-defined]
        ws = tmp_path / "ws"
        ws.mkdir()
        created = c.app.state.project_store.create(
            name="memory-insert",
            workspace_path=str(ws),
            template="attach",
        )
        c._test_project_id = str(created.project_id)  # type: ignore[attr-defined]
        c._test_chunk_store = chunk_store  # type: ignore[attr-defined]
        c._test_ws = ws  # type: ignore[attr-defined]
        yield c


def test_insert_memory_chunk_into_run_api(memory_client: TestClient) -> None:
    pid = memory_client._test_project_id  # type: ignore[attr-defined]
    chunk_store: InMemoryMemoryChunkStore = memory_client._test_chunk_store  # type: ignore[attr-defined]
    ws: Path = memory_client._test_ws  # type: ignore[attr-defined]
    scope = repo_scope_hash(ws)
    chunk_id = uuid4()
    run_id = uuid4()
    chunk_store.replace_generation(
        org_scope_hash=scope,
        repo_scope_hash=scope,
        embedding_mode="deterministic",
        embedding_model_id="test",
        chunks=[
            MemoryChunkRecord(
                chunk_id=chunk_id,
                generation_id=uuid4(),
                repo_scope_hash=scope,
                run_id=run_id,
                source_event_type="finding.created",
                category="security",
                severity="HIGH",
                excerpt="Validate auth on every route",
                embedding_model_id="test",
                embedding_dim=8,
                embedding_vector=[0.0] * 8,
            ),
        ],
        manifest_relpath=None,
    )
    project = memory_client.app.state.project_store.get(UUID(pid))
    assert project is not None
    store = memory_client.app.state.store
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
    resp = memory_client.post(f"/v1/runs/{run_id}/memory-chunks/{chunk_id}/insert")
    assert resp.status_code == 200
    rows = store.list_run_events(str(run_id))
    inserted = [
        row
        for row in rows
        if (row.get("payload") or {}).get("stage_name") == "campaign.memory.chunk.inserted"
    ]
    assert len(inserted) == 1
