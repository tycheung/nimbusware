"""Advisory run context budget estimates for Maker and API."""

from __future__ import annotations

from typing import Any, Literal

from agent_core.context_budget import estimate_tokens
from agent_core.models import EventType
from agent_core.models.slice_packet import SliceContextPacket

AdvisoryLevel = Literal["green", "amber", "red"]

_TIER_WINDOW_DEFAULTS: dict[str, int] = {
    "weak": 8192,
    "medium": 32768,
    "strong": 131072,
}


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("payload")
    return dict(raw) if isinstance(raw, dict) else {}


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("metadata")
    return dict(raw) if isinstance(raw, dict) else {}


def window_tokens_from_events(events: list[dict[str, Any]]) -> int:
    """Resolve model context window from preflight or cached hardware tier."""
    from nimbusware_projections.builders.preflight import preflight_timeline_summary

    pf = preflight_timeline_summary(events)
    if pf:
        ctx = pf.get("context_tokens")
        if isinstance(ctx, int) and ctx > 0:
            return ctx
    try:
        from nimbusware_hw.cache import get_cached_profile

        profile = get_cached_profile()
        return _TIER_WINDOW_DEFAULTS.get(str(profile.tier or "weak"), 8192)
    except (ImportError, OSError, TypeError, ValueError):
        return 8192


def _latest_slice_packet_char_count(events: list[dict[str, Any]]) -> int:
    latest = 0
    for row in events:
        if row.get("event_type") not in {
            EventType.STAGE_PASSED.value,
            EventType.STAGE_FAILED.value,
        }:
            continue
        if _payload(row).get("stage_name") != "slice.gate":
            continue
        packet = _metadata(row).get("slice_context_packet")
        if not isinstance(packet, dict):
            continue
        try:
            model = SliceContextPacket.model_validate(packet)
            latest = model.char_count()
        except (TypeError, ValueError):
            latest = len(str(packet))
    return latest


def _latest_handoff_char_count(events: list[dict[str, Any]]) -> int:
    latest = 0
    for row in events:
        if _payload(row).get("stage_name") != "slice.handoff":
            continue
        meta = _metadata(row)
        summary = meta.get("handoff_summary")
        if isinstance(summary, str) and summary.strip():
            latest = len(summary)
    return latest


def _latest_compaction_char_count(events: list[dict[str, Any]]) -> int:
    latest = 0
    for row in events:
        if _payload(row).get("stage_name") != "campaign.context.compacted":
            continue
        meta = _metadata(row)
        summary = meta.get("summary")
        if isinstance(summary, str) and summary.strip():
            latest = len(summary)
    return latest


def advisory_level_for_ratio(ratio: float) -> AdvisoryLevel:
    if ratio < 0.30:
        return "green"
    if ratio <= 0.70:
        return "amber"
    return "red"


def estimate_context_budget(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum planner-facing context components and compare to window (advisory only)."""
    slice_chars = _latest_slice_packet_char_count(events)
    handoff_chars = _latest_handoff_char_count(events)
    compaction_chars = _latest_compaction_char_count(events)
    estimated_chars = slice_chars + handoff_chars + compaction_chars
    estimated_tokens = estimate_tokens("x" * estimated_chars) if estimated_chars else 0
    window_tokens = window_tokens_from_events(events)
    ratio = (estimated_tokens / window_tokens) if window_tokens > 0 else 0.0
    return {
        "estimated_chars": estimated_chars,
        "estimated_tokens": estimated_tokens,
        "window_tokens": window_tokens,
        "utilization_ratio": round(ratio, 4),
        "advisory_level": advisory_level_for_ratio(ratio),
        "components": {
            "slice_packet_chars": slice_chars,
            "handoff_chars": handoff_chars,
            "compaction_summary_chars": compaction_chars,
        },
        "advisory_only": True,
    }
