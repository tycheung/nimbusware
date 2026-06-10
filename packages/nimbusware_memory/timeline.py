"""Memory timeline read-model helpers (shared by API + replay)."""

from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType


def memory_retrieval_timeline_entries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ev in events:
        if ev.get("event_type") != EventType.MEMORY_RETRIEVAL_EMITTED.value:
            continue
        payload_raw = ev.get("payload")
        pl: dict[str, Any] = payload_raw if isinstance(payload_raw, dict) else {}
        hit_ids = pl.get("hit_chunk_ids") or []
        out.append(
            {
                "stage_name": pl.get("stage_name"),
                "slice_id": pl.get("slice_id"),
                "retrieval_k": pl.get("retrieval_k"),
                "excerpt_chars": pl.get("excerpt_chars"),
                "hit_count": len(hit_ids) if isinstance(hit_ids, list) else 0,
                "hit_chunk_ids": list(hit_ids)[:20] if isinstance(hit_ids, list) else [],
                "query_digest": pl.get("query_digest"),
                "occurred_at": ev.get("occurred_at"),
            },
        )
    return out


def memory_retrieval_entries_for_slice(
    events: list[dict[str, Any]],
    slice_id: str,
) -> list[dict[str, Any]]:
    """Filter retrieval timeline rows for one slice."""
    sid = slice_id.strip()
    if not sid:
        return []
    return [row for row in memory_retrieval_timeline_entries(events) if row.get("slice_id") == sid]


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
    pl = mapping_or_empty(last.get("payload"))
    return {
        "index_event_count": len(indexed),
        "chunks_added": pl.get("chunks_added"),
        "chunks_skipped": pl.get("chunks_skipped"),
        "generation_id": pl.get("generation_id"),
        "embedding_mode": pl.get("embedding_mode"),
    }
