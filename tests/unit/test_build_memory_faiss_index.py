"""Tests for ``scripts/build_memory_faiss_index.py``."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from hermes_memory import InMemoryMemoryChunkStore, rebuild_memory_index
from hermes_memory.faiss_index import memory_faiss_index_ready
from hermes_memory.models import MemoryChunkRecord
from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_build_memory_faiss_index_help() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_memory_faiss_index.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "--repo-root" in proc.stdout


@pytest.mark.skipif(
    importlib.util.find_spec("faiss") is None,
    reason="optional faiss group not installed",
)
def test_rebuild_writes_memory_faiss_index(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    from agent_core.models import EventType

    rid = uuid4()
    rows = [
        {
            "store_seq": 1,
            "run_id": rid,
            "event_type": EventType.RUN_CREATED.value,
            "metadata": {},
            "payload": {},
        },
        {
            "store_seq": 2,
            "run_id": rid,
            "event_type": EventType.FINDING_CREATED.value,
            "payload": {"finding_id": str(uuid4()), "category": "gate"},
        },
    ]
    store = InMemoryMemoryChunkStore()
    rebuild_memory_index(store, repo_root=tmp_path, in_memory_event_rows=rows)
    idx_dir = tmp_path / "configs" / "memory" / "index"
    assert memory_faiss_index_ready(idx_dir)


def test_memory_faiss_search_chunk_ids(tmp_path) -> None:
    pytest.importorskip("faiss")
    from hermes_memory.embeddings import deterministic_embed
    from hermes_memory.faiss_index import build_memory_faiss_index, faiss_search_chunk_ids

    gid = uuid4()
    chunks = [
        MemoryChunkRecord(
            chunk_id=uuid4(),
            generation_id=gid,
            repo_scope_hash="abc123",
            run_id=uuid4(),
            source_event_type="finding.created",
            excerpt="sql injection failure",
            embedding_model_id="test",
            embedding_dim=32,
            embedding_vector=deterministic_embed("sql injection failure"),
        ),
        MemoryChunkRecord(
            chunk_id=uuid4(),
            generation_id=gid,
            repo_scope_hash="abc123",
            run_id=uuid4(),
            source_event_type="finding.created",
            excerpt="network timeout retry",
            embedding_model_id="test",
            embedding_dim=32,
            embedding_vector=deterministic_embed("network timeout retry"),
        ),
    ]
    idx_dir = tmp_path / "index"
    assert build_memory_faiss_index(chunks=chunks, index_dir=idx_dir) == 0
    hits = faiss_search_chunk_ids(
        idx_dir,
        deterministic_embed("sql injection"),
        k=1,
    )
    assert hits == [chunks[0].chunk_id]
