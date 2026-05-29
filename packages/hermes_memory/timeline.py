"""Memory timeline read-model helpers (shared by API + replay)."""

from __future__ import annotations

from typing import Any

from agent_core.models import EventType


def memory_retrieval_timeline_entries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ev in events:
        if ev.get("event_type") != EventType.MEMORY_RETRIEVAL_EMITTED.value:
            continue
        pl = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
        out.append(
            {
                "stage_name": pl.get("stage_name"),
                "retrieval_k": pl.get("retrieval_k"),
                "excerpt_chars": pl.get("excerpt_chars"),
                "hit_count": len(pl.get("hit_chunk_ids") or []),
                "query_digest": pl.get("query_digest"),
                "occurred_at": ev.get("occurred_at"),
            },
        )
    return out


def memory_retrieval_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    hist = memory_retrieval_timeline_entries(events)
    if not hist:
        return None
    last = hist[-1]
    return {
        "retrieval_count": len(hist),
        "last_stage_name": last.get("stage_name"),
        "last_excerpt_chars": last.get("excerpt_chars"),
        "last_hit_count": last.get("hit_count"),
        "last_query_digest": last.get("query_digest"),
    }


def memory_indexed_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    indexed = [ev for ev in events if ev.get("event_type") == EventType.MEMORY_INDEXED.value]
    if not indexed:
        return None
    last = indexed[-1]
    pl = last.get("payload") if isinstance(last.get("payload"), dict) else {}
    return {
        "index_event_count": len(indexed),
        "chunks_added": pl.get("chunks_added"),
        "chunks_skipped": pl.get("chunks_skipped"),
        "generation_id": pl.get("generation_id"),
        "embedding_mode": pl.get("embedding_mode"),
    }
