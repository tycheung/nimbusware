from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from memory.peel_index.models import MemoryChunkRecord


def memory_faiss_index_ready(index_dir: Path) -> bool:
    if not index_dir.is_dir():
        return False
    if (index_dir / "faiss.index").is_file():
        return True
    order = index_dir / "chunk_order.json"
    vectors = index_dir / "vectors.json"
    return order.is_file() and vectors.is_file()


def build_memory_faiss_index(
    *,
    chunks: list[MemoryChunkRecord],
    index_dir: Path,
) -> dict[str, Any]:
    index_dir.mkdir(parents=True, exist_ok=True)
    order = [str(c.chunk_id) for c in chunks]
    (index_dir / "chunk_order.json").write_text(json.dumps(order), encoding="utf-8")
    vectors = [c.embedding_vector for c in chunks]
    if not vectors:
        return {"chunk_count": 0, "faiss": False}
    dim = len(vectors[0])
    mat = np.asarray(vectors, dtype=np.float32)
    (index_dir / "vectors.json").write_text(
        json.dumps(mat.tolist()),
        encoding="utf-8",
    )
    try:
        import faiss

        index = faiss.IndexFlatIP(dim)
        index.add(mat)
        faiss.write_index(index, str(index_dir / "faiss.index"))
        return {"chunk_count": len(chunks), "faiss": True}
    except ImportError:
        return {"chunk_count": len(chunks), "faiss": False}
