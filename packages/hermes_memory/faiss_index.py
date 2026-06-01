"""Optional FAISS index for repo-scoped memory chunks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np

from hermes_memory.models import MemoryChunkRecord


def memory_faiss_index_ready(index_dir: Path) -> bool:
    """Return True when both FAISS index files exist under ``index_dir``."""
    return (index_dir / "faiss.index").is_file() and (index_dir / "chunk_order.json").is_file()


def build_memory_faiss_index(
    *,
    chunks: list[MemoryChunkRecord],
    index_dir: Path,
) -> int:
    """Write ``faiss.index`` + ``chunk_order.json`` from chunk embeddings. Returns exit code."""
    if not chunks:
        return 1
    try:
        import faiss
    except ImportError:
        return 1

    index_dir.mkdir(parents=True, exist_ok=True)
    order = [str(ch.chunk_id) for ch in chunks]
    dim = int(chunks[0].embedding_dim)
    mat = np.stack(
        [np.asarray(ch.embedding_vector, dtype=np.float32) for ch in chunks],
        axis=0,
    ).astype(np.float32)
    if mat.shape[1] != dim:
        return 1
    index = faiss.IndexFlatIP(dim)
    index.add(mat)
    faiss.write_index(index, str(index_dir / "faiss.index"))
    order_json = json.dumps(order)
    (index_dir / "chunk_order.json").write_text(order_json, encoding="utf-8")
    (index_dir / "memory_order.json").write_text(order_json, encoding="utf-8")
    return 0


def try_load_memory_faiss(
    index_dir: Path,
) -> tuple[Any, list[str]] | None:
    """Load FAISS index and chunk id order when files exist and ``faiss`` is installed."""
    if not memory_faiss_index_ready(index_dir):
        return None
    try:
        import faiss
    except ImportError:
        return None
    index = faiss.read_index(str(index_dir / "faiss.index"))
    order: list[str] = json.loads((index_dir / "chunk_order.json").read_text(encoding="utf-8"))
    return (index, order)


def faiss_search_chunk_ids(
    index_dir: Path,
    query_vector: list[float],
    *,
    k: int,
) -> list[UUID]:
    """Return top-k chunk ids via FAISS inner product (vectors must be normalized)."""
    loaded = try_load_memory_faiss(index_dir)
    if loaded is None:
        return []
    index, order = loaded
    if not order:
        return []
    q = np.asarray(query_vector, dtype=np.float32).reshape(1, -1)
    _, inds = index.search(q, min(k, len(order)))
    out: list[UUID] = []
    for i in inds[0]:
        idx = int(i)
        if idx < 0 or idx >= len(order):
            continue
        try:
            out.append(UUID(order[idx]))
        except ValueError:
            continue
    return out
