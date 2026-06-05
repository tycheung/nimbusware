from __future__ import annotations

from agent_core.models import EventType
from nimbusware_env import env_flags
from nimbusware_memory.timeline import (
    memory_indexed_timeline_summary,
    memory_retrieval_timeline_entries,
    memory_retrieval_timeline_summary,
)


def test_memory_timeline_summaries_empty() -> None:
    assert memory_retrieval_timeline_entries([]) == []
    assert memory_retrieval_timeline_summary([]) is None
    assert memory_indexed_timeline_summary([]) is None


def test_memory_timeline_with_sample_events() -> None:
    events = [
        {
            "event_type": EventType.MEMORY_RETRIEVAL_EMITTED.value,
            "payload": {
                "stage_name": "slice.plan",
                "retrieval_k": 3,
                "excerpt_chars": 120,
                "hit_chunk_ids": ["a", "b"],
                "query_digest": "abc",
            },
            "occurred_at": "2026-01-01T00:00:00Z",
        },
        {
            "event_type": EventType.MEMORY_INDEXED.value,
            "payload": {
                "chunks_added": 2,
                "chunks_skipped": 0,
                "generation_id": "gen-1",
                "embedding_mode": "deterministic",
            },
        },
    ]
    assert len(memory_retrieval_timeline_entries(events)) == 1
    summary = memory_retrieval_timeline_summary(events)
    assert summary is not None
    assert summary["retrieval_count"] == 1
    indexed = memory_indexed_timeline_summary(events)
    assert indexed is not None
    assert indexed["chunks_added"] == 2


def test_env_flags_public_helpers() -> None:
    assert isinstance(env_flags.nimbusware_skip_preflight_enabled(), bool)
    assert isinstance(env_flags.nimbusware_use_llm_enabled(), bool)
    assert isinstance(env_flags.env_truthy("NIMBUSWARE_NOT_SET_TEST_FLAG_XYZ"), bool)
