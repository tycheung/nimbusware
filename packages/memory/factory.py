from __future__ import annotations

from env.env_flags import nimbusware_database_url
from memory.store.memory import InMemoryMemoryChunkStore
from memory.store.postgres import PostgresMemoryChunkStore
from memory.store.protocol import MemoryChunkStore


def build_memory_chunk_store(
    conninfo: str | None = None,
    *,
    allow_in_memory: bool = False,
) -> MemoryChunkStore | None:
    url = (conninfo or nimbusware_database_url() or "").strip()
    if url:
        return PostgresMemoryChunkStore(url)
    if allow_in_memory:
        return InMemoryMemoryChunkStore()
    return None
