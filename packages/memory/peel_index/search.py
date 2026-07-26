from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np

from memory.peel_index.embeddings import embed_text
from memory.peel_index.models import EmbeddingMode, MemoryRetrievalHit
from memory.peel_index.repo_scope import repo_scope_hash
from memory.peel_index.user_scope import user_memory_index_dir
from memory.peel_store.protocol import MemoryChunkStore


def _cosine(a: list[float], b: list[float]) -> float:
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb)) + 1e-9
    return float(np.dot(va, vb) / denom)


def _hits_from_chunks(
    chunks: list[Any],
    query: str,
    *,
    k: int,
    embedding_mode: EmbeddingMode,
) -> list[MemoryRetrievalHit]:
    if not chunks:
        return []
    qvec = embed_text(query, mode=embedding_mode)
    scored: list[MemoryRetrievalHit] = []
    for ch in chunks:
        score = _cosine(qvec, ch.embedding_vector)
        scored.append(
            MemoryRetrievalHit(
                chunk_id=ch.chunk_id,
                excerpt=ch.excerpt,
                score=score,
                run_id=ch.run_id,
                category=ch.category,
            ),
        )
    scored.sort(key=lambda h: h.score, reverse=True)
    return scored[: max(1, k)]


def search_memory(
    memory_store: MemoryChunkStore | None,
    query: str,
    *,
    repo_root: Path,
    k: int = 5,
    embedding_mode: EmbeddingMode = "deterministic",
) -> list[MemoryRetrievalHit]:
    if memory_store is None:
        return []
    scope = repo_scope_hash(repo_root)
    chunks = memory_store.list_chunks_for_scope(scope)
    return _hits_from_chunks(chunks, query, k=k, embedding_mode=embedding_mode)


def _user_scope_hash(repo_root: Path, user_id: str) -> str:
    path = user_memory_index_dir(repo_root, user_id)
    return hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:16]


def search_user_memory(
    memory_store: MemoryChunkStore | None,
    query: str,
    *,
    user_id: str,
    repo_root: Path,
    k: int = 5,
    embedding_mode: EmbeddingMode = "deterministic",
) -> list[MemoryRetrievalHit]:
    if memory_store is None:
        return []
    uid = user_id.strip()
    if not uid:
        return []
    scope = _user_scope_hash(repo_root, uid)
    chunks = memory_store.list_chunks_for_scope(scope)
    return _hits_from_chunks(chunks, query, k=k, embedding_mode=embedding_mode)


def search_fleet_memory(
    memory_store: MemoryChunkStore | None,
    query: str,
    *,
    org_scope_hash: str,
    tenant_id: UUID | None = None,
    k: int = 5,
    embedding_mode: EmbeddingMode = "deterministic",
) -> list[MemoryRetrievalHit]:
    if memory_store is None:
        return []
    chunks = memory_store.list_chunks_for_org_scope(org_scope_hash, tenant_id=tenant_id)
    return _hits_from_chunks(chunks, query, k=k, embedding_mode=embedding_mode)


def format_memory_excerpt(
    hits: list[MemoryRetrievalHit],
    *,
    max_chars: int = 2000,
) -> str:
    if max_chars <= 0 or not hits:
        return ""
    parts: list[str] = []
    used = 0
    for i, hit in enumerate(hits, start=1):
        block = f"[{i}] score={hit.score:.2f} chunk={hit.chunk_id}\n{hit.excerpt.strip()}"
        if used + len(block) + 2 > max_chars:
            break
        parts.append(block)
        used += len(block) + 2
    return "\n\n".join(parts)


def pinned_generation_id(
    memory_store: MemoryChunkStore | None,
    *,
    repo_root: Path,
) -> UUID | None:
    if memory_store is None:
        return None
    scope = repo_scope_hash(repo_root)
    row = memory_store.latest_generation(repo_scope_hash=scope)
    return row.generation_id if row is not None else None
