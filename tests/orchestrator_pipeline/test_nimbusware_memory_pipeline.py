from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agent_core.models import EventType
from env import find_repo_root
from memory import InMemoryMemoryChunkStore, rebuild_memory_index
from orchestrator.micro_slice import parse_slice_plan
from orchestrator.pipeline import make_dev_orchestrator


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
    ]


def test_rebuild_emits_memory_indexed_audit(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    from store.memory import InMemoryEventStore

    event_store = InMemoryEventStore()
    mem_store = InMemoryMemoryChunkStore()
    audit_run = uuid4()
    rebuild_memory_index(
        mem_store,
        repo_root=tmp_path,
        in_memory_event_rows=_sample_rows(),
        audit_store=event_store,
        audit_run_id=audit_run,
    )
    rows = event_store._rows  # noqa: SLF001 — test inspects append-only store
    assert any(r["event_type"] == EventType.MEMORY_INDEXED.value for r in rows)
    indexed = next(r for r in rows if r["event_type"] == EventType.MEMORY_INDEXED.value)
    assert indexed["run_id"] == audit_run


def test_record_micro_slice_gate_injects_memory_excerpt() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    mem_store = InMemoryMemoryChunkStore()
    rebuild_memory_index(
        mem_store,
        repo_root=repo,
        in_memory_event_rows=_sample_rows(),
    )
    orch, store = make_dev_orchestrator(repo, memory_chunk_store=mem_store)
    run_id = orch.create_run("micro_slice")
    plan = parse_slice_plan(
        {
            "slice_id": "slice-mem",
            "target_paths": ["packages/memory/search.py"],
            "rationale": "sql injection fix",
        },
    )
    orch.record_micro_slice_plan(run_id, plan)
    gate = orch.record_micro_slice_gate(
        run_id,
        plan,
        verify_ok=True,
        critique_verdicts=["PASS"],
        tests_passed=True,
    )
    assert gate.passed
    rows = store.list_run_events(str(run_id))
    gate_rows = [
        r
        for r in rows
        if (r.get("payload") or {}).get("stage_name") == "slice.gate"
        and (r.get("metadata") or {}).get("slice_context_packet")
    ]
    assert gate_rows
    packet = (gate_rows[-1].get("metadata") or {}).get("slice_context_packet") or {}
    assert packet.get("memory_excerpt")
    retrieval_rows = [
        r for r in rows if r.get("event_type") == EventType.MEMORY_RETRIEVAL_EMITTED.value
    ]
    assert retrieval_rows
