"""Insert indexed memory chunks into an active run timeline."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from nimbusware_memory.models import MemoryChunkRecord


def insert_memory_chunk_into_run(
    store: object,
    *,
    run_id: object,
    chunk: MemoryChunkRecord,
) -> dict[str, Any]:
    from datetime import datetime, timezone
    from uuid import uuid4

    from agent_core.models import EventType, StageStartedEvent, StageStartedPayload

    store.append(  # type: ignore[attr-defined]
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,  # type: ignore[arg-type]
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "chunk_id": str(chunk.chunk_id),
                "run_id": str(chunk.run_id),
                "category": chunk.category,
                "severity": chunk.severity,
                "excerpt": chunk.excerpt[:8000],
                "source_event_type": chunk.source_event_type,
            },
            payload=StageStartedPayload(
                stage_name="campaign.memory.chunk.inserted",
                attempt=1,
            ),
        ),
    )
    return {
        "chunk_id": str(chunk.chunk_id),
        "category": chunk.category,
        "severity": chunk.severity,
    }


def find_memory_chunk_for_scope(
    memory_store: object,
    *,
    repo_scope_hash: str,
    chunk_id: UUID,
) -> MemoryChunkRecord | None:
    rows = memory_store.list_chunks_for_scope(repo_scope_hash)  # type: ignore[attr-defined]
    target = str(chunk_id)
    for row in rows:
        if str(row.chunk_id) == target:
            return cast(MemoryChunkRecord, row)
    return None
