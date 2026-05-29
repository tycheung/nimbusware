"""Append-only audit events for memory index lifecycle (Phase 4 / fo161)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    MemoryIndexedEvent,
    MemoryIndexedPayload,
    MemoryRetrievalEmittedEvent,
    MemoryRetrievalEmittedPayload,
)

from hermes_memory.indexer import RebuildIndexResult
from hermes_memory.models import MemoryRetrievalHit

if TYPE_CHECKING:
    from hermes_store.protocol import EventStore


def append_memory_indexed_event(
    store: EventStore,
    *,
    run_id: UUID,
    result: RebuildIndexResult,
) -> None:
    """Persist ``memory.indexed`` after a successful rebuild."""
    index_dir = str(result.manifest_path.parent)
    store.append(
        MemoryIndexedEvent(
            event_type=EventType.MEMORY_INDEXED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=MemoryIndexedPayload(
                repo_scope_hash=result.repo_scope_hash,
                generation_id=str(result.generation_id),
                chunks_added=result.chunks_added,
                chunks_skipped=result.chunks_skipped,
                embedding_mode=result.embedding_mode,
                embedding_model_id=result.embedding_model_id,
                index_dir=index_dir,
            ),
        ),
    )


def append_memory_retrieval_emitted_event(
    store: EventStore,
    *,
    run_id: UUID,
    stage_name: str,
    query_digest: str,
    hits: list[MemoryRetrievalHit],
    excerpt: str,
    retrieval_k: int,
    repo_scope_hash: str,
    generation_id: UUID | None,
) -> None:
    """Persist ``memory.retrieval.emitted`` when hits are injected into a stage."""
    store.append(
        MemoryRetrievalEmittedEvent(
            event_type=EventType.MEMORY_RETRIEVAL_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=MemoryRetrievalEmittedPayload(
                stage_name=stage_name,
                query_digest=query_digest,
                hit_chunk_ids=[str(h.chunk_id) for h in hits],
                excerpt_chars=len(excerpt),
                retrieval_k=retrieval_k,
                repo_scope_hash=repo_scope_hash,
                generation_id=str(generation_id) if generation_id else None,
            ),
        ),
    )
