from __future__ import annotations

from agent_core.models.slice_handoff import SliceHandoffSummary
from uuid import uuid4

from nimbusware_orchestrator.context_compaction import (
    compact_campaign_context,
    maybe_emit_compaction_event,
)
from nimbusware_store.memory import InMemoryEventStore


def _handoff_event(
    sid: str,
    *,
    seq: int,
    summary: str,
) -> dict:
    handoff = SliceHandoffSummary(
        goal="campaign",
        progress=(f"{sid}: passed",),
        modified_files=(f"packages/{sid}.py",),
    )
    return {
        "seq": seq,
        "payload": {"stage_name": "slice.handoff"},
        "metadata": {
            "slice_id": sid,
            "handoff_summary": summary,
            "slice_handoff": handoff.model_dump(),
        },
    }


def test_compaction_bounds_tokens_for_many_slices() -> None:
    events: list[dict] = []
    for i in range(100):
        text = f"## Goal\ncampaign\n## Progress\n- slice-{i}: passed\n" + ("x" * 200)
        events.append(_handoff_event(f"slice-{i}", seq=i + 1, summary=text))

    single = estimate_single_slice_prompt(events[-1])
    result = compact_campaign_context(events, keep_recent_tokens=2000, reserve_tokens=500)
    assert result is not None
    assert result.tokens_after <= max(result.tokens_before // 2, single * 2)


def estimate_single_slice_prompt(event: dict) -> int:
    from agent_core.context_budget import estimate_tokens

    meta = event.get("metadata") or {}
    return estimate_tokens(str(meta.get("handoff_summary") or ""))


def test_compaction_emits_summary_with_merged_progress() -> None:
    events = [
        _handoff_event("slice-1", seq=1, summary="a" * 500),
        _handoff_event("slice-2", seq=2, summary="b" * 500),
        _handoff_event("slice-3", seq=3, summary="c" * 500),
        _handoff_event("slice-4", seq=4, summary="d" * 500),
    ]
    result = compact_campaign_context(events, keep_recent_tokens=150, reserve_tokens=50)
    assert result is not None
    assert result.handoff.progress
    assert result.tokens_after < result.tokens_before


def test_maybe_emit_compaction_event_appends_marker() -> None:
    store = InMemoryEventStore()
    run_id = uuid4()
    events = [
        _handoff_event("slice-1", seq=1, summary="a" * 500),
        _handoff_event("slice-2", seq=2, summary="b" * 500),
        _handoff_event("slice-3", seq=3, summary="c" * 500),
        _handoff_event("slice-4", seq=4, summary="d" * 500),
    ]
    result = maybe_emit_compaction_event(
        store,
        run_id=run_id,
        events=events,
        keep_recent_tokens=150,
        reserve_tokens=50,
    )
    assert result is not None
    rows = store.list_run_events(str(run_id))
    assert any(
        (r.get("payload") or {}).get("stage_name") == "campaign.context.compacted"
        for r in rows
    )
