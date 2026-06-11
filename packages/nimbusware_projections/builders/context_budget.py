from __future__ import annotations

from typing import Any, Literal

from agent_core.context_budget import estimate_tokens
from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType
from agent_core.models.slice_packet import SliceContextPacket

AdvisoryLevel = Literal["green", "amber", "red"]

_TIER_WINDOW_DEFAULTS: dict[str, int] = {
    "weak": 8192,
    "medium": 32768,
    "strong": 131072,
}


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    return mapping_or_empty(row.get("payload"))


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    return mapping_or_empty(row.get("metadata"))


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


def _reverted_compaction_ids(events: list[dict[str, Any]]) -> set[str]:
    from nimbusware_orchestrator.context_compaction import reverted_compaction_ids

    return reverted_compaction_ids(events)


def _latest_compaction_row(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    reverted = _reverted_compaction_ids(events)
    latest: dict[str, Any] | None = None
    latest_seq = -1
    for row in events:
        if _payload(row).get("stage_name") != "campaign.context.compacted":
            continue
        meta = _metadata(row)
        cid = str(meta.get("compaction_id") or "").strip()
        if cid and cid in reverted:
            continue
        seq = int(row.get("store_seq") or 0)
        if seq >= latest_seq:
            latest_seq = seq
            latest = row
    return latest


def _latest_compaction_char_count(events: list[dict[str, Any]]) -> int:
    row = _latest_compaction_row(events)
    if row is None:
        return 0
    summary = _metadata(row).get("summary")
    if isinstance(summary, str) and summary.strip():
        return len(summary)
    return 0


def _last_compaction_detail(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    row = _latest_compaction_row(events)
    if row is None:
        return None
    meta = _metadata(row)
    return {
        "occurred_at": row.get("occurred_at"),
        "store_seq": int(row.get("store_seq") or 0),
        "tokens_before": meta.get("tokens_before"),
        "tokens_after": meta.get("tokens_after"),
        "merged_handoff_count": meta.get("merged_handoff_count"),
        "trigger": meta.get("compaction_trigger"),
        "compaction_id": meta.get("compaction_id"),
        "summary": meta.get("summary") if isinstance(meta.get("summary"), str) else None,
    }


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
    out: dict[str, Any] = {
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
    last = _last_compaction_detail(events)
    if last is not None:
        out["last_compaction"] = last
    return out
