from __future__ import annotations

from console.critic_reliability_display import (
    critic_reliability_caption,
    critic_reliability_summary_from_events,
    critic_reliability_table_rows,
)


def test_critic_reliability_summary() -> None:
    events = [
        {
            "event_type": "critic.verdict.emitted",
            "payload": {"verdict": "FAIL", "critic_role": "security"},
        },
        {
            "event_type": "critic.verdict.emitted",
            "payload": {"verdict": "PASS", "critic_role": "planner"},
        },
        {
            "event_type": "gate.decision.emitted",
            "payload": {"verdict": "FAIL", "stage_name": "implementation"},
        },
        {
            "event_type": "finding.created",
            "payload": {"stage_name": "slice.gate", "message": "budget exceeded"},
        },
        {
            "event_type": "finding.created",
            "payload": {"stage_name": "slice.gate", "message": "budget exceeded"},
        },
    ]
    summary = critic_reliability_summary_from_events(events)
    assert summary["critic_verdict_count"] == 2
    assert summary["critic_fail_count"] == 1
    assert summary["critic_fail_rate"] == 0.5
    assert summary["gate_block_count"] == 1
    assert summary["repeat_finding_paths"] == 1
    rows = critic_reliability_table_rows(summary)
    assert len(rows) == 5
    assert "50.0%" in critic_reliability_caption(summary)
