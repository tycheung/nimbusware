from __future__ import annotations

import math
from pathlib import Path
from uuid import UUID

from nimbusware_memory.embeddings import embed_text
from nimbusware_memory.faiss_index import faiss_search_chunk_ids, try_load_memory_faiss
from nimbusware_memory.manifest import default_memory_index_dir, latest_generation_id
from nimbusware_memory.models import EmbeddingMode, MemoryChunkRecord, MemoryRetrievalHit
from nimbusware_memory.repo_scope import repo_scope_hash, resolve_repo_root
from nimbusware_memory.store import MemoryChunkStore


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def search_memory(
    memory_store: MemoryChunkStore,
    query: str,
    *,
    repo_root: Path | None = None,
    k: int = 5,
    embedding_mode: EmbeddingMode = "deterministic",
) -> list[MemoryRetrievalHit]:
    """Top-k chunks by cosine similarity (repo-scoped; FAISS when index present)."""
    root = resolve_repo_root(repo_root)
    scope = repo_scope_hash(root)
    qvec = embed_text(query.strip(), mode=embedding_mode)
    chunks = memory_store.list_chunks_for_scope(scope)
    if not chunks:
        return []
    kk = max(1, min(20, int(k)))
    index_dir = default_memory_index_dir(root)
    if try_load_memory_faiss(index_dir) is not None:
        by_id = {ch.chunk_id: ch for ch in chunks}
        hits: list[MemoryRetrievalHit] = []
        for cid in faiss_search_chunk_ids(index_dir, qvec, k=kk):
            ch = by_id.get(cid)
            if ch is None:
                continue
            score = _cosine(qvec, ch.embedding_vector)
            hits.append(_hit_from_chunk(ch, score))
        if hits:
            return hits
    return _brute_force_search(qvec, chunks, k=kk)


def search_fleet_memory(
    memory_store: MemoryChunkStore,
    query: str,
    *,
    org_scope_hash: str,
    tenant_id: UUID | None = None,
    repo_root: Path | None = None,
    k: int = 5,
    embedding_mode: EmbeddingMode = "deterministic",
) -> list[MemoryRetrievalHit]:
    """Top-k fleet/org-scoped chunks (Enterprise)."""
    from nimbusware_memory.org_scope import require_fleet_memory_feature

    require_fleet_memory_feature()
    qvec = embed_text(query.strip(), mode=embedding_mode)
    chunks = memory_store.list_chunks_for_org_scope(org_scope_hash, tenant_id=tenant_id)
    if not chunks:
        return []
    kk = max(1, min(20, int(k)))
    root = resolve_repo_root(repo_root)
    index_dir = root / "configs" / "memory" / "fleet" / org_scope_hash
    if try_load_memory_faiss(index_dir) is not None:
        by_id = {ch.chunk_id: ch for ch in chunks}
        hits: list[MemoryRetrievalHit] = []
        for cid in faiss_search_chunk_ids(index_dir, qvec, k=kk):
            ch = by_id.get(cid)
            if ch is None:
                continue
            score = _cosine(qvec, ch.embedding_vector)
            hits.append(_hit_from_chunk(ch, score))
        if hits:
            return hits
    return _brute_force_search(qvec, chunks, k=kk)


def _hit_from_chunk(ch: MemoryChunkRecord, score: float) -> MemoryRetrievalHit:
    return MemoryRetrievalHit(
        chunk_id=ch.chunk_id,
        excerpt=ch.excerpt,
        score=score,
        run_id=ch.run_id,
        category=ch.category,
    )


def _brute_force_search(
    qvec: list[float],
    chunks: list[MemoryChunkRecord],
    *,
    k: int,
) -> list[MemoryRetrievalHit]:
    scored: list[tuple[float, MemoryRetrievalHit]] = []
    for ch in chunks:
        score = _cosine(qvec, ch.embedding_vector)
        scored.append((score, _hit_from_chunk(ch, score)))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [hit for _, hit in scored[:k]]


def format_memory_excerpt(hits: list[MemoryRetrievalHit], *, max_chars: int) -> str:
    if not hits or max_chars <= 0:
        return ""
    parts: list[str] = []
    used = 0
    for i, hit in enumerate(hits, start=1):
        block = f"[{i}] run={hit.run_id} score={hit.score:.3f}\n{hit.excerpt}"
        if used + len(block) + 2 > max_chars:
            break
        parts.append(block)
        used += len(block) + 2
    return "\n\n".join(parts)


def pinned_generation_id(
    memory_store: MemoryChunkStore,
    *,
    repo_root: Path | None = None,
) -> UUID | None:
    root = resolve_repo_root(repo_root)
    scope = repo_scope_hash(root)
    gen = memory_store.latest_generation(scope)
    if gen is not None:
        return gen.generation_id
    return latest_generation_id(default_memory_index_dir(root))
