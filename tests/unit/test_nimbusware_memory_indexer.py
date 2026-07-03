from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from agent_core.models import EventType, Verdict
from memory import (
    InMemoryMemoryChunkStore,
    rebuild_memory_index,
    repo_scope_hash,
    search_memory,
)
from memory.manifest import read_manifest


def _sample_rows() -> list[dict]:
    rid = uuid4()
    return [
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
            "payload": {
                "finding_id": str(uuid4()),
                "category": "sql_injection",
                "severity": "critical",
                "source_artifact": "sql_profiler",
            },
        },
        {
            "store_seq": 3,
            "run_id": rid,
            "event_type": EventType.GATE_DECISION_EMITTED.value,
            "payload": {
                "stage_name": "security_scan",
                "verdict": Verdict.FAIL.value,
                "failing_critics": ["sql_profiler"],
            },
        },
    ]


def test_rebuild_memory_index_in_memory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    store = InMemoryMemoryChunkStore()
    result = rebuild_memory_index(
        store,
        repo_root=tmp_path,
        in_memory_event_rows=_sample_rows(),
    )
    assert result.chunks_added == 2
    assert result.chunks_skipped == 0
    scope = repo_scope_hash(tmp_path)
    assert result.repo_scope_hash == scope
    manifest = read_manifest(tmp_path / "configs" / "memory" / "index")
    assert manifest is not None
    assert manifest.chunk_count == 2
    assert manifest.generation_id == str(result.generation_id)
    gen = store.latest_generation(scope)
    assert gen is not None
    assert gen.chunk_count == 2
    hits = search_memory(store, "sql injection profiler", repo_root=tmp_path, k=3)
    assert hits
    assert all(h.score > 0 for h in hits)


def test_manifest_written_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    store = InMemoryMemoryChunkStore()
    rebuild_memory_index(store, repo_root=tmp_path, in_memory_event_rows=_sample_rows())
    path = tmp_path / "configs" / "memory" / "index" / "manifest.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1
    assert raw["embedding_mode"] == "deterministic"
