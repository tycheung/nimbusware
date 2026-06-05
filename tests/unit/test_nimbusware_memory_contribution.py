from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from agent_core.models import EventType
from nimbusware_memory import InMemoryMemoryChunkStore
from nimbusware_memory.contribution import maybe_rebuild_memory_index_for_run
from nimbusware_memory.embeddings import deterministic_embed, embed_text
from nimbusware_memory.sync import memory_index_sync_state, memory_sync_manifest_stub
from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_store.memory import InMemoryEventStore
from nimbusware_env import find_repo_root


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


@pytest.mark.parametrize("pressure_level", ["warn", "throttle", "block"])
def test_maybe_rebuild_defers_under_ram_pressure(
    tmp_path,
    monkeypatch,
    pressure_level: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    store = InMemoryEventStore()
    mem = InMemoryMemoryChunkStore()
    run_id = uuid4()

    def _fake_pressure(_gov):
        return pressure_level, {"reason": "ram_over_cap"}

    monkeypatch.setattr("nimbusware_hw.pressure.sample_pressure", _fake_pressure)
    monkeypatch.setattr(
        "nimbusware_hw.governor.governor_from_metadata",
        lambda _meta: object(),
    )
    result = maybe_rebuild_memory_index_for_run(
        mem,
        store,
        run_id=run_id,
        repo_root=tmp_path,
        run_created_metadata={
            "memory": {"index_contribution": True},
            "resource_governor": {"max_system_ram_pct": 75},
        },
    )
    assert result is None
    rows = store.list_all_event_rows()
    assert not any(r["event_type"] == EventType.MEMORY_INDEXED.value for r in rows)
    assert any(r["event_type"] == EventType.RESOURCE_PRESSURE_WARN.value for r in rows)


def test_maybe_rebuild_emits_memory_indexed(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "nimbusware_hw.pressure.sample_pressure",
        lambda _gov: ("ok", {}),
    )
    monkeypatch.setattr(
        "nimbusware_hw.governor.governor_from_metadata",
        lambda _meta: object(),
    )
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
    assert any(
        r["event_type"] == EventType.MEMORY_INDEXED.value for r in store.list_all_event_rows()
    )


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
