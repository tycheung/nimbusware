"""Memory retrieval timeline filtered by slice_id."""

from __future__ import annotations

from hermes_memory.timeline import (
    memory_retrieval_entries_for_slice,
    memory_retrieval_timeline_entries,
)


def test_filter_retrievals_by_slice_id() -> None:
    events = [
        {
            "event_type": "memory.retrieval.emitted",
            "payload": {
                "stage_name": "slice.gate",
                "slice_id": "slice-a",
                "query_digest": "a" * 16,
                "hit_chunk_ids": ["c1", "c2"],
                "excerpt_chars": 100,
                "retrieval_k": 5,
                "repo_scope_hash": "b" * 16,
            },
        },
        {
            "event_type": "memory.retrieval.emitted",
            "payload": {
                "stage_name": "slice.gate",
                "slice_id": "slice-b",
                "query_digest": "c" * 16,
                "hit_chunk_ids": ["c3"],
                "excerpt_chars": 50,
                "retrieval_k": 3,
                "repo_scope_hash": "d" * 16,
            },
        },
    ]
    rows = memory_retrieval_entries_for_slice(events, "slice-a")
    assert len(rows) == 1
    assert rows[0]["slice_id"] == "slice-a"
    assert rows[0]["hit_count"] == 2
    assert len(memory_retrieval_timeline_entries(events)) == 2
