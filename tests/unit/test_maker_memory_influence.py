from __future__ import annotations

from nimbusware_maker.memory_influence_display import format_retrieval_rows


def test_format_retrieval_rows_truncates_digest() -> None:
    rows = format_retrieval_rows(
        [
            {
                "stage_name": "slice.gate",
                "hit_count": 2,
                "excerpt_chars": 80,
                "query_digest": "abcdef0123456789",
                "hit_chunk_ids": ["chunk-one", "chunk-two"],
                "occurred_at": "2026-01-01T00:00:00Z",
            },
        ],
    )
    assert rows[0]["stage"] == "slice.gate"
    assert rows[0]["hits"] == "2"
    assert "chunk-one" in rows[0]["chunk_ids"]
