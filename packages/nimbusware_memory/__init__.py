"""Nimbusware agent retrieval memory: repo-scoped failure/fix index."""

from nimbusware_memory.audit import (
    append_memory_indexed_event,
    append_memory_retrieval_emitted_event,
)
from nimbusware_memory.chunking import chunks_from_event_rows, run_index_contribution_enabled
from nimbusware_memory.embeddings import deterministic_embed, embedding_model_id_for_mode
from nimbusware_memory.faiss_index import build_memory_faiss_index, memory_faiss_index_ready
from nimbusware_memory.indexer import RebuildIndexResult, rebuild_memory_index
from nimbusware_memory.manifest import MemoryIndexManifest, default_memory_index_dir, write_manifest
from nimbusware_memory.models import (
    EmbeddingMode,
    MemoryChunkDraft,
    MemoryChunkRecord,
    MemoryRetrievalHit,
)
from nimbusware_memory.repo_scope import repo_scope_hash
from nimbusware_memory.search import format_memory_excerpt, search_memory
from nimbusware_memory.store import InMemoryMemoryChunkStore, PostgresMemoryChunkStore

__all__ = [
    "EmbeddingMode",
    "InMemoryMemoryChunkStore",
    "MemoryChunkDraft",
    "MemoryChunkRecord",
    "MemoryIndexManifest",
    "MemoryRetrievalHit",
    "PostgresMemoryChunkStore",
    "RebuildIndexResult",
    "append_memory_indexed_event",
    "append_memory_retrieval_emitted_event",
    "build_memory_faiss_index",
    "chunks_from_event_rows",
    "default_memory_index_dir",
    "deterministic_embed",
    "embedding_model_id_for_mode",
    "format_memory_excerpt",
    "memory_faiss_index_ready",
    "rebuild_memory_index",
    "repo_scope_hash",
    "run_index_contribution_enabled",
    "search_memory",
    "write_manifest",
]
