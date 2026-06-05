"""Optional memory chunk store factory."""

from __future__ import annotations

import os

from nimbusware_memory.store import (
    InMemoryMemoryChunkStore,
    MemoryChunkStore,
    PostgresMemoryChunkStore,
)


def build_memory_chunk_store(
    conninfo: str | None = None,
    *,
    allow_in_memory: bool = False,
) -> MemoryChunkStore | None:
    """Return Postgres store when ``NIMBUSWARE_DATABASE_URL`` is set; else optional in-memory."""
    url = (conninfo or os.environ.get("NIMBUSWARE_DATABASE_URL", "")).strip()
    if url:
        return PostgresMemoryChunkStore(url)
    if allow_in_memory:
        return InMemoryMemoryChunkStore()
    return None
