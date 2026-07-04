from __future__ import annotations

from memory.index.models import MemoryRetrievalHit


def build_memory_index_table(
    hits: list[MemoryRetrievalHit],
    *,
    max_chars: int = 1500,
) -> str:
    """Compact index-only memory table for prompt injection (no full bodies)."""
    if not hits or max_chars <= 0:
        return ""
    lines = ["| id | score | category | preview |", "|---|---:|---|---|"]
    used = sum(len(line) for line in lines)
    for hit in hits:
        preview = hit.excerpt.replace("\n", " ").strip()[:80]
        cat = hit.category or "-"
        row = f"| {hit.chunk_id} | {hit.score:.2f} | {cat} | {preview} |"
        if used + len(row) + 1 > max_chars:
            break
        lines.append(row)
        used += len(row) + 1
    return "\n".join(lines)
