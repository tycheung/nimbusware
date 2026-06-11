from __future__ import annotations

from nimbusware_orchestrator.interjection_slo import (
    interjection_slo_markdown,
    interjection_slo_summary,
)


def _enqueue(at: str, message: str = "fix auth") -> dict:
    return {
        "event_type": "stage.started",
        "occurred_at": at,
        "payload": {"stage_name": "interjection.enqueued"},
        "metadata": {"interjection": {"message": message, "priority": "next"}},
    }


def _drain(at: str) -> dict:
    return {
        "event_type": "stage.started",
        "occurred_at": at,
        "payload": {"stage_name": "interjection.drained"},
        "metadata": {"interjection": {"count": 1}},
    }


def _slice_plan(at: str) -> dict:
    return {
        "event_type": "stage.started",
        "occurred_at": at,
        "payload": {"stage_name": "slice.plan"},
    }


def test_interjection_slo_met_when_drained_before_next_slice() -> None:
    events = [
        _enqueue("2026-06-01T10:00:00Z"),
        _drain("2026-06-01T10:00:30Z"),
        _slice_plan("2026-06-01T10:01:00Z"),
    ]
    summary = interjection_slo_summary(events)
    assert summary["slo_met"] is True
    assert summary["overdue_count"] == 0


def test_interjection_slo_breach_when_not_drained_before_next_slice() -> None:
    events = [
        _enqueue("2026-06-01T10:00:00Z", "urgent steer"),
        _slice_plan("2026-06-01T10:01:00Z"),
    ]
    summary = interjection_slo_summary(events)
    assert summary["slo_met"] is False
    assert summary["overdue_count"] == 1
    md = interjection_slo_markdown(summary)
    assert "SLO breach" in md
    assert "urgent steer" in md


def test_pending_queue_counts_as_overdue() -> None:
    summary = interjection_slo_summary([], pending_queue_count=2)
    assert summary["overdue_count"] == 1
    assert summary["pending_queue_count"] == 2
