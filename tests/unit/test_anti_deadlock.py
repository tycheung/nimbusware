"""Anti-deadlock escalation pure logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hermes_orchestrator.anti_deadlock import should_emit_anti_deadlock_escalation


def test_no_escalation_when_disabled() -> None:
    now = datetime.now(timezone.utc)
    rows = [{"store_seq": 1, "event_type": "run.created", "occurred_at": now}]
    assert not should_emit_anti_deadlock_escalation(
        rows,
        now=now,
        enabled=False,
        stall_minutes=1,
        min_progress_events=1,
    )


def test_escalates_when_stalled_and_no_progress() -> None:
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    rows = [
        {
            "store_seq": 1,
            "event_type": "run.created",
            "occurred_at": t0,
            "payload": {},
        },
        {
            "store_seq": 2,
            "event_type": "model.preflight.passed",
            "occurred_at": t0,
            "payload": {},
        },
    ]
    now = t0 + timedelta(minutes=60)
    assert should_emit_anti_deadlock_escalation(
        rows,
        now=now,
        enabled=True,
        stall_minutes=30,
        min_progress_events=2,
    )


def test_no_escalation_when_progress_sufficient() -> None:
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    rows = [
        {"store_seq": 1, "event_type": "run.created", "occurred_at": t0, "payload": {}},
        {"store_seq": 2, "event_type": "model.preflight.passed", "occurred_at": t0, "payload": {}},
        {"store_seq": 3, "event_type": "run.started", "occurred_at": t0, "payload": {}},
    ]
    now = t0 + timedelta(minutes=60)
    assert not should_emit_anti_deadlock_escalation(
        rows,
        now=now,
        enabled=True,
        stall_minutes=30,
        min_progress_events=1,
    )
