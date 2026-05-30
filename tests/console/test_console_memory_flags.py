from __future__ import annotations

from nimbusware_console.memory_display import (
    memory_policy_from_run_summary,
    memory_policy_table_rows,
    memory_retrieval_timeline_entries,
    memory_retrieval_timeline_summary,
)


def test_memory_policy_from_run_summary() -> None:
    summary = {
        "run_created_metadata": {
            "memory": {
                "retrieval_enabled": False,
                "index_contribution": True,
                "embedding_mode": "deterministic",
            },
        },
    }
    policy = memory_policy_from_run_summary(summary)
    assert policy is not None
    assert policy["retrieval_enabled"] is False
    rows = memory_policy_table_rows(policy)
    assert any(r["field"] == "embedding_mode" for r in rows)


def test_memory_retrieval_timeline_summary() -> None:
    events = [
        {
            "event_type": "memory.retrieval.emitted",
            "occurred_at": "2026-01-01T00:00:00Z",
            "payload": {
                "stage_name": "slice.gate",
                "retrieval_k": 5,
                "excerpt_chars": 100,
                "hit_chunk_ids": ["a"],
                "query_digest": "deadbeefdeadbeef",
            },
        },
    ]
    assert len(memory_retrieval_timeline_entries(events)) == 1
    summary = memory_retrieval_timeline_summary(events)
    assert summary is not None
    assert summary["last_hit_count"] == 1
