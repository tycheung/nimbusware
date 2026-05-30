from __future__ import annotations
from nimbusware_env import find_repo_root

from pathlib import Path
from uuid import uuid4

from agent_core.models import EventType
from hermes_memory import InMemoryMemoryChunkStore
from hermes_memory.contribution import maybe_rebuild_memory_index_for_run
from hermes_memory.sync import memory_index_sync_state, memory_sync_manifest_stub
from hermes_memory.embeddings import deterministic_embed, embed_text
from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_store.memory import InMemoryEventStore
from nimbusware_console.memory_display import (
    memory_policy_from_run_summary,
    memory_retrieval_timeline_summary,
)


def test_embed_text_deterministic_stable() -> None:
    a = embed_text("hello memory", mode="deterministic")
    b = embed_text("hello memory", mode="deterministic")
    assert a == b
    assert len(a) == len(deterministic_embed("hello memory"))


def test_embed_text_ollama_falls_back_without_llm_flag() -> None:
    vec = embed_text("hello", mode="ollama")
    assert vec == deterministic_embed("hello")


def test_maybe_rebuild_skips_when_index_contribution_false() -> None:
    store = InMemoryEventStore()
    mem = InMemoryMemoryChunkStore()
    run_id = uuid4()
    result = maybe_rebuild_memory_index_for_run(
        mem,
        store,
        run_id=run_id,
        repo_root=Path("."),
        run_created_metadata={"memory": {"index_contribution": False}},
    )
    assert result is None


def test_maybe_rebuild_emits_memory_indexed(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    store = InMemoryEventStore()
    mem = InMemoryMemoryChunkStore()
    run_id = uuid4()
    rows = [
        {
            "store_seq": 1,
            "run_id": run_id,
            "event_type": EventType.RUN_CREATED.value,
            "metadata": {"memory": {"index_contribution": True}},
            "payload": {},
        },
        {
            "store_seq": 2,
            "run_id": run_id,
            "event_type": EventType.FINDING_CREATED.value,
            "payload": {
                "finding_id": str(uuid4()),
                "category": "sql_injection",
                "severity": "critical",
            },
        },
    ]
    for row in rows:
        store._rows.append(row)  # noqa: SLF001
    result = maybe_rebuild_memory_index_for_run(
        mem,
        store,
        run_id=run_id,
        repo_root=tmp_path,
        run_created_metadata={"memory": {"index_contribution": True}},
    )
    assert result is not None
    assert result.chunks_added >= 1
    assert any(r["event_type"] == EventType.MEMORY_INDEXED.value for r in store.list_all_event_rows())


def test_create_run_pins_memory_index_version(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    mem_store = InMemoryMemoryChunkStore()
    orch, store = make_dev_orchestrator(repo, memory_chunk_store=mem_store)
    run_id = orch.create_run("nimbusware_production")
    meta = orch._run_created_metadata(run_id)
    assert meta.get("memory", {}).get("retrieval_enabled") is True
    assert "memory_index_version" in meta.get("memory", {}) or meta.get("memory_effective")


def test_memory_index_sync_state_without_faiss(tmp_path: Path) -> None:
    state = memory_index_sync_state(tmp_path)
    assert state["faiss_ready"] is False


def test_memory_sync_manifest_stub(tmp_path: Path) -> None:
    stub = memory_sync_manifest_stub(tmp_path)
    assert stub["remote_sync"] == "not_configured"
