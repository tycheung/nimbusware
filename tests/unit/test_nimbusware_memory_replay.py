from __future__ import annotations

from uuid import uuid4

from agent_core.models import EventType
from orchestrator.replay.harness import (
    build_replay_snapshot,
    diff_replay_snapshots,
    stable_replay_hash,
)


def _minimal_rows() -> list[dict]:
    rid = uuid4()
    return [
        {
            "store_seq": 1,
            "event_id": uuid4(),
            "run_id": rid,
            "event_type": EventType.RUN_CREATED.value,
            "occurred_at": "2026-01-15T12:00:00Z",
            "metadata": {},
            "payload": {
                "workflow_profile": "micro_slice",
                "policy_version": "1",
                "config_snapshot_id": "cfg-test",
            },
        },
        {
            "store_seq": 2,
            "event_id": uuid4(),
            "run_id": rid,
            "event_type": EventType.RUN_COMPLETED.value,
            "occurred_at": "2026-01-15T12:00:01Z",
            "payload": {"summary": "done"},
        },
    ]


def test_build_replay_snapshot_terminal_run() -> None:
    rows = _minimal_rows()
    snap = build_replay_snapshot(rows, run_id=str(rows[0]["run_id"]))
    assert snap["summary"]["status"] == "terminal"
    assert snap["event_count"] == 2
    assert snap["memory_retrieval"] is None


def test_stable_replay_hash_is_deterministic() -> None:
    rows = _minimal_rows()
    snap = build_replay_snapshot(rows, run_id=str(rows[0]["run_id"]))
    assert stable_replay_hash(snap) == stable_replay_hash(snap)


def test_diff_replay_snapshots_reports_differences() -> None:
    rows = _minimal_rows()
    rid = str(rows[0]["run_id"])
    left = build_replay_snapshot(rows, run_id=rid)
    right = build_replay_snapshot(rows, run_id=rid)
    assert diff_replay_snapshots(left, right) == []
    right["event_count"] = 99
    lines = diff_replay_snapshots(left, right)
    assert lines and "event_count" in lines[0]
