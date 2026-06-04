from __future__ import annotations

from uuid import uuid4

from agent_core.models import EventType, Verdict
from hermes_research.stitch_outcome_stats import compute_stitch_transplant_stats


def _row(
    *,
    run_id,
    store_seq: int,
    event_type: str,
    payload: dict | None = None,
) -> dict:
    return {
        "run_id": run_id,
        "store_seq": store_seq,
        "event_type": event_type,
        "payload": payload or {},
    }


def test_stitch_stats_pass_after_gate() -> None:
    run_id = uuid4()
    rows = [
        _row(run_id=run_id, store_seq=1, event_type=EventType.STITCH_APPLIED.value),
        _row(
            run_id=run_id,
            store_seq=2,
            event_type=EventType.GATE_DECISION_EMITTED.value,
            payload={"verdict": Verdict.PASS.value},
        ),
    ]
    stats = compute_stitch_transplant_stats(rows)
    assert stats["runs_with_stitch"] == 1
    assert stats["transplant_pass"] == 1
    assert stats["transplant_fail"] == 0
    assert stats["pass_rate_pct"] == 100.0


def test_stitch_stats_fail_after_stitch_failed() -> None:
    run_id = uuid4()
    rows = [
        _row(run_id=run_id, store_seq=1, event_type=EventType.STITCH_APPLIED.value),
        _row(run_id=run_id, store_seq=2, event_type=EventType.STITCH_FAILED.value),
    ]
    stats = compute_stitch_transplant_stats(rows)
    assert stats["transplant_fail"] == 1
    assert stats["pass_rate_pct"] == 0.0


def test_stitch_stats_ignores_runs_without_stitch() -> None:
    run_id = uuid4()
    rows = [
        _row(
            run_id=run_id,
            store_seq=1,
            event_type=EventType.GATE_DECISION_EMITTED.value,
            payload={"verdict": Verdict.PASS.value},
        ),
    ]
    stats = compute_stitch_transplant_stats(rows)
    assert stats["runs_with_stitch"] == 0
    assert stats["sample_size"] == 0
    assert stats["pass_rate_pct"] is None
