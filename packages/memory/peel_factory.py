from __future__ import annotations

from typing import Any

from env.env_flags import nimbusware_database_url
from memory.peel_store.memory import InMemoryMemoryChunkStore


def build_memory_chunk_store(*, allow_in_memory: bool = True) -> Any:
    url = nimbusware_database_url()
    if url:
        try:
            from memory.peel_store.postgres import PostgresMemoryChunkStore

            return PostgresMemoryChunkStore(url)
        except (ImportError, RuntimeError, ValueError):
            if not allow_in_memory:
                return None
    if allow_in_memory:
        return InMemoryMemoryChunkStore()
    return None
