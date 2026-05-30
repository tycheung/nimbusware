from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import (
    EventType,
    MemoryIndexedEvent,
    MemoryIndexedPayload,
    MemoryRetrievalEmittedEvent,
    MemoryRetrievalEmittedPayload,
    serialize_event_persistent,
    validate_event_dict,
)


def test_memory_indexed_event_validates() -> None:
    rid = uuid4()
    payload = MemoryIndexedPayload(
        repo_scope_hash="a" * 16,
        generation_id=str(uuid4()),
        chunks_added=3,
        chunks_skipped=1,
        embedding_mode="deterministic",
        embedding_model_id="hermes-memory-deterministic-v1",
        index_dir="configs/memory/index",
    )
    ev = MemoryIndexedEvent(
        event_type=EventType.MEMORY_INDEXED,
        event_id=uuid4(),
        run_id=rid,
        occurred_at=datetime.now(timezone.utc),
        payload=payload,
    )
    back = validate_event_dict(serialize_event_persistent(ev))
    assert back.event_type == EventType.MEMORY_INDEXED


def test_memory_retrieval_emitted_event_validates() -> None:
    rid = uuid4()
    payload = MemoryRetrievalEmittedPayload(
        stage_name="micro_slice",
        query_digest="deadbeef" * 2,
        hit_chunk_ids=[str(uuid4())],
        excerpt_chars=120,
        retrieval_k=5,
        repo_scope_hash="b" * 16,
        generation_id=str(uuid4()),
    )
    ev = MemoryRetrievalEmittedEvent(
        event_type=EventType.MEMORY_RETRIEVAL_EMITTED,
        event_id=uuid4(),
        run_id=rid,
        occurred_at=datetime.now(timezone.utc),
        payload=payload,
    )
    back = validate_event_dict(serialize_event_persistent(ev))
    assert back.event_type == EventType.MEMORY_RETRIEVAL_EMITTED
