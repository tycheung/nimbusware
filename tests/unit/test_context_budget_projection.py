from __future__ import annotations

from agent_core.models import EventType
from projections.builders.context_budget import (
    advisory_level_for_ratio,
    estimate_context_budget,
    window_tokens_from_events,
)


def test_advisory_levels() -> None:
    assert advisory_level_for_ratio(0.1) == "green"
    assert advisory_level_for_ratio(0.5) == "amber"
    assert advisory_level_for_ratio(0.9) == "red"


def test_estimate_context_budget_sums_components() -> None:
    events = [
        {
            "event_type": EventType.MODEL_PREFLIGHT_PASSED.value,
            "payload": {"context_tokens": 10000},
        },
        {
            "event_type": EventType.STAGE_PASSED.value,
            "payload": {"stage_name": "slice.gate"},
            "metadata": {
                "slice_context_packet": {
                    "slice_id": "s1",
                    "diff_unified": "a" * 4000,
                    "handoff_summary": "b" * 500,
                },
            },
        },
        {
            "event_type": EventType.STAGE_STARTED.value,
            "payload": {"stage_name": "slice.handoff"},
            "metadata": {"handoff_summary": "c" * 300},
        },
        {
            "event_type": EventType.STAGE_STARTED.value,
            "payload": {"stage_name": "campaign.context.compacted"},
            "metadata": {"summary": "d" * 200},
        },
    ]
    budget = estimate_context_budget(events)
    assert budget["window_tokens"] == 10000
    assert budget["components"]["slice_packet_chars"] >= 4500
    assert budget["components"]["handoff_chars"] == 300
    assert budget["components"]["compaction_summary_chars"] == 200
    assert budget["advisory_level"] in {"green", "amber", "red"}
    assert budget["advisory_only"] is True


def test_window_tokens_fallback_to_hw_tier(monkeypatch) -> None:
    class _Profile:
        tier = "medium"

    monkeypatch.setattr(
        "hw.cache.get_cached_profile",
        lambda **_: _Profile(),
    )
    assert window_tokens_from_events([]) == 32768
