from __future__ import annotations

from broker_client.flags import broker_memory_enabled
from broker_client.stage_bind import memory_search_via_broker


def try_broker_memory_search(query: str, *, limit: int | None = None) -> dict | None:
    """Return broker memory search result when enabled.

    Disabled (``=0``): ``None``.
    Peel (``=1|2``): return result or re-raise on failure (`sak494-d`).
    """
    if not broker_memory_enabled():
        return None
    return memory_search_via_broker(query, limit=limit)
