from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from memory.embeddings import embed_text
from memory.models import MemoryChunkRecord
from memory.search import search_user_memory
from memory.store import InMemoryMemoryChunkStore
from memory.user_scope import user_scope_hash


def test_search_user_memory_returns_hits(tmp_path: Path) -> None:
    store = InMemoryMemoryChunkStore()
    scope = user_scope_hash("alice")
    vec = embed_text("sql timeout profiler", mode="deterministic")
    gen = uuid4()
    chunk = MemoryChunkRecord(
        chunk_id=uuid4(),
        generation_id=gen,
        repo_scope_hash=scope,
        run_id=uuid4(),
        source_event_type="test",
        source_store_seq=1,
        finding_id=None,
        category="test",
        severity="info",
        excerpt="sql timeout profiler gate",
        embedding_model_id="det",
        embedding_dim=len(vec),
        embedding_vector=vec,
    )
    store.replace_generation(
        generation_id=gen,
        org_scope_hash=scope,
        repo_scope_hash=scope,
        embedding_mode="deterministic",
        embedding_model_id="det",
        chunks=[chunk],
        manifest_relpath=None,
    )
    hits = search_user_memory(store, "sql timeout", user_id="alice", repo_root=tmp_path, k=3)
    assert hits
    assert hits[0].excerpt.startswith("sql")
