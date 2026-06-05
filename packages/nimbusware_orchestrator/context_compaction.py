"""Campaign-level context compaction for long multi-slice runs."""

from __future__ import annotations

from dataclasses import dataclass

from agent_core.context_budget import estimate_tokens
from agent_core.models.slice_handoff import SliceHandoffSummary
from nimbusware_orchestrator.slice_handoff import (
    build_slice_handoff_summary,
    handoff_markdown_capped,
)


@dataclass(frozen=True)
class CompactionResult:
    summary: str
    tokens_before: int
    tokens_after: int
    kept_event_seq_range: tuple[int, int]
    handoff: SliceHandoffSummary


def campaign_compact_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_CAMPAIGN_COMPACT_ENABLED", default=True)


def _default_keep_recent_tokens() -> int:
    from nimbusware_env.env_flags import nimbusware_campaign_keep_recent_tokens

    return nimbusware_campaign_keep_recent_tokens()


def _default_reserve_tokens() -> int:
    from nimbusware_env.env_flags import nimbusware_campaign_reserve_tokens

    return nimbusware_campaign_reserve_tokens()


def _handoff_events(events: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for row in events:
        payload = row.get("payload") or {}
        if isinstance(payload, dict) and payload.get("stage_name") == "slice.handoff":
            rows.append(row)
    return rows


def compact_campaign_context(
    events: list[dict],
    *,
    keep_recent_tokens: int | None = None,
    reserve_tokens: int | None = None,
) -> CompactionResult | None:
    """Summarize older slice handoffs; keep recent verbatim within token budget."""
    if not campaign_compact_enabled():
        return None
    handoffs = _handoff_events(events)
    if len(handoffs) < 3:
        return None

    keep = keep_recent_tokens if keep_recent_tokens is not None else _default_keep_recent_tokens()
    reserve = reserve_tokens if reserve_tokens is not None else _default_reserve_tokens()
    keep = max(1, keep - max(0, reserve))

    recent: list[dict] = []
    older: list[dict] = []
    token_budget = 0
    for row in reversed(handoffs):
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        summary_text = str(meta.get("handoff_summary") or "")
        tokens = estimate_tokens(summary_text)
        if token_budget + tokens <= keep:
            recent.insert(0, row)
            token_budget += tokens
        else:
            older.insert(0, row)

    if not older:
        return None

    merged = _merge_handoffs(older)
    recent_text = "\n\n".join(
        str((r.get("metadata") or {}).get("handoff_summary") or "")
        for r in recent
        if isinstance(r.get("metadata"), dict)
    )
    tokens_before = estimate_tokens(
        "\n\n".join(
            str((r.get("metadata") or {}).get("handoff_summary") or "")
            for r in handoffs
            if isinstance(r.get("metadata"), dict)
        ),
    )
    compact_summary = handoff_markdown_capped(merged)
    if recent_text.strip():
        compact_summary = f"{compact_summary}\n\n## Recent verbatim\n{recent_text}"
    tokens_after = estimate_tokens(compact_summary)

    seqs = [int(r.get("seq") or 0) for r in handoffs if r.get("seq") is not None]
    kept_range = (min(seqs), max(seqs)) if seqs else (0, 0)

    return CompactionResult(
        summary=compact_summary,
        tokens_before=tokens_before,
        tokens_after=tokens_after,
        kept_event_seq_range=kept_range,
        handoff=merged,
    )


def _merge_handoffs(rows: list[dict]) -> SliceHandoffSummary:
    merged: SliceHandoffSummary | None = None
    for row in rows:
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        raw = meta.get("slice_handoff")
        if not isinstance(raw, dict):
            continue
        handoff = SliceHandoffSummary.model_validate(raw)
        if merged is None:
            merged = handoff
            continue
        merged = build_slice_handoff_summary(
            _dummy_plan(handoff.progress[-1] if handoff.progress else "slice"),
            prior=merged,
            paths_touched=handoff.modified_files,
            diff_stat="compacted",
        )
    return merged or SliceHandoffSummary(goal="(compacted campaign context)")


def _dummy_plan(label: str) -> object:
    from nimbusware_orchestrator.micro_slice import parse_slice_plan

    return parse_slice_plan(
        {
            "slice_id": label.split(":")[0] if ":" in label else "slice-compact",
            "target_paths": [],
            "rationale": "compaction merge",
        },
    )


def maybe_emit_compaction_event(
    store: object,
    *,
    run_id: object,
    events: list[dict],
    keep_recent_tokens: int | None = None,
    reserve_tokens: int | None = None,
) -> CompactionResult | None:
    """Compact when enabled and append a campaign.context.compacted marker event."""
    result = compact_campaign_context(
        events,
        keep_recent_tokens=keep_recent_tokens,
        reserve_tokens=reserve_tokens,
    )
    if result is None:
        return None
    from datetime import datetime, timezone
    from uuid import uuid4

    from agent_core.models import EventType, StageStartedEvent, StageStartedPayload

    store.append(  # type: ignore[attr-defined]
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,  # type: ignore[arg-type]
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "campaign_context_compacted": True,
                "summary": result.summary,
                "tokens_before": result.tokens_before,
                "tokens_after": result.tokens_after,
                "kept_event_seq_range": list(result.kept_event_seq_range),
                "slice_handoff": result.handoff.model_dump(mode="json"),
            },
            payload=StageStartedPayload(stage_name="campaign.context.compacted", attempt=1),
        ),
    )
    return result
