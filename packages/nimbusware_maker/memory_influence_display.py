from __future__ import annotations

from typing import Any


def format_retrieval_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        hits = row.get("hit_chunk_ids") or []
        hit_preview = ", ".join(str(h)[:12] for h in hits[:5])
        if len(hits) > 5:
            hit_preview += f" (+{len(hits) - 5} more)"
        digest = str(row.get("query_digest") or "")
        out.append(
            {
                "stage": str(row.get("stage_name") or ""),
                "hits": str(row.get("hit_count") or 0),
                "excerpt_chars": str(row.get("excerpt_chars") or 0),
                "query_digest": digest[:16] + "…" if len(digest) > 16 else digest,
                "chunk_ids": hit_preview or "—",
                "occurred_at": str(row.get("occurred_at") or ""),
            },
        )
    return out
