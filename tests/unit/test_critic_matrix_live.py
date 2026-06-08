"""Live orchestration critic matrix."""

from __future__ import annotations

from nimbusware_orchestrator.critic_matrix_live import (
    build_live_critic_matrix_rows,
    critic_matrix_unanimous_summary,
)


def _run_created(stage_names: list[str]) -> dict:
    return {
        "event_type": "run.created",
        "metadata": {
            "stage_graph": {
                "ordered_stage_names": stage_names,
                "nodes": [],
                "parallel_groups": {},
            },
        },
    }


def test_live_matrix_pending_when_gate_missing() -> None:
    events = [
        _run_created(["implementation.critique", "test_writer.critique"]),
    ]
    rows = build_live_critic_matrix_rows(events)
    assert len(rows) == 2
    assert all(r["verdict"] == "PENDING" for r in rows)
    summary = critic_matrix_unanimous_summary(rows)
    assert summary["pending_count"] == 2
    assert summary["pass_count"] == 0


def test_live_matrix_merges_gate_decisions() -> None:
    events = [
        _run_created(["implementation.critique", "test_writer.critique"]),
        {
            "event_type": "gate.decision.emitted",
            "event_id": "g1",
            "occurred_at": "2026-01-01T00:00:00Z",
            "metadata": {"parallel_group": "writers", "stage_graph_order_index": 2},
            "payload": {
                "stage_name": "implementation.critique",
                "verdict": "PASS",
                "unanimous_pass_required": True,
                "failing_critics": [],
            },
        },
    ]
    rows = build_live_critic_matrix_rows(events)
    impl = next(r for r in rows if r["stage_name"] == "implementation.critique")
    tw = next(r for r in rows if r["stage_name"] == "test_writer.critique")
    assert impl["verdict"] == "PASS"
    assert impl["parallel_group"] == "writers"
    assert tw["verdict"] == "PENDING"
    summary = critic_matrix_unanimous_summary(rows)
    assert summary["pass_count"] == 1
    assert summary["pending_count"] == 1


def test_live_matrix_summary_collects_failing_critics() -> None:
    events = [
        _run_created(["implementation.critique"]),
        {
            "event_type": "gate.decision.emitted",
            "event_id": "g2",
            "occurred_at": "2026-01-01T00:00:00Z",
            "metadata": {},
            "payload": {
                "stage_name": "implementation.critique",
                "verdict": "FAIL",
                "failing_critics": ["critic.alpha", "critic.beta"],
                "unanimous_pass_required": True,
            },
        },
    ]
    rows = build_live_critic_matrix_rows(events)
    summary = critic_matrix_unanimous_summary(rows)
    assert summary["fail_count"] == 1
    assert summary["failing_critics"] == ["critic.alpha", "critic.beta"]
