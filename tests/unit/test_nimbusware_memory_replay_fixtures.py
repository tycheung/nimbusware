from __future__ import annotations

from pathlib import Path

import pytest

from agent_core.models import EventType
from nimbusware_memory import InMemoryMemoryChunkStore, rebuild_memory_index, search_memory
from nimbusware_memory.indexer import deterministic_chunk_id
from nimbusware_orchestrator.replay_cli import main as replay_cli_main
from nimbusware_orchestrator.replay_harness import (
    build_replay_snapshot,
    load_fixture_rows,
    stable_replay_hash,
)

_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "memory" / "failure_pattern_events.json"
)
_GOLDEN_REPLAY_HASH = "4608af5e53064660b7e3e38699bb1833a55a8e60d94ba00e6ea0756843db6542"


def test_failure_pattern_fixture_replay_hash_stable() -> None:
    run_id, rows = load_fixture_rows(_FIXTURE)
    snapshot = build_replay_snapshot(rows, run_id=run_id)
    assert snapshot["summary"]["status"] == "terminal"
    assert snapshot["summary"]["findings_count"] == 1
    assert snapshot["event_types"][-2:] == [
        EventType.MEMORY_INDEXED.value,
        EventType.MEMORY_RETRIEVAL_EMITTED.value,
    ]
    assert snapshot["memory_retrieval"] is not None
    assert snapshot["memory_retrieval"]["last_query_digest"] == "fixture-query-digest-v1"
    digest = stable_replay_hash(snapshot)
    assert digest == _GOLDEN_REPLAY_HASH


def test_replay_cli_fixture_hash_mode(capsys) -> None:
    code = replay_cli_main(["--fixture", str(_FIXTURE), "--hash"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    assert out == _GOLDEN_REPLAY_HASH


def test_failure_pattern_index_rebuild_stable_chunk_ids(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _, rows = load_fixture_rows(_FIXTURE)
    store = InMemoryMemoryChunkStore()

    rebuild_memory_index(store, repo_root=tmp_path, in_memory_event_rows=rows)
    hits_a = search_memory(store, "sql injection profiler gate", repo_root=tmp_path, k=3)
    ids_a = [str(h.chunk_id) for h in hits_a]

    rebuild_memory_index(store, repo_root=tmp_path, in_memory_event_rows=rows)
    hits_b = search_memory(store, "sql injection profiler gate", repo_root=tmp_path, k=3)
    ids_b = [str(h.chunk_id) for h in hits_b]

    assert ids_a
    assert ids_a == ids_b
    assert all(h.category in {"sql_injection", "gate"} for h in hits_a)


def test_deterministic_chunk_id_matches_indexer(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _, rows = load_fixture_rows(_FIXTURE)
    store = InMemoryMemoryChunkStore()
    result = rebuild_memory_index(store, repo_root=tmp_path, in_memory_event_rows=rows)
    scope = result.repo_scope_hash
    chunks = store.list_chunks_for_scope(scope)
    finding_row = next(r for r in rows if r["event_type"] == EventType.FINDING_CREATED.value)
    pl = finding_row["payload"]
    from uuid import UUID

    from nimbusware_memory.chunking import _finding_excerpt

    expected_finding = deterministic_chunk_id(
        repo_scope_hash=scope,
        run_id=UUID(str(finding_row["run_id"])),
        source_event_type=EventType.FINDING_CREATED.value,
        source_store_seq=int(finding_row["store_seq"]),
        excerpt=_finding_excerpt(pl),
    )
    chunk_ids = {str(ch.chunk_id) for ch in chunks}
    assert str(expected_finding) in chunk_ids


@pytest.mark.parametrize(
    ("argv", "expected_code"),
    [
        ([], 2),
        (["not-a-uuid"], 2),
    ],
)
def test_replay_cli_requires_input(argv: list[str], expected_code: int) -> None:
    with pytest.raises(SystemExit) as exc:
        replay_cli_main(argv)
    assert exc.value.code == expected_code
