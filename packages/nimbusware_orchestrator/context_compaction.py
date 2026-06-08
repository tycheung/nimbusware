"""Campaign-level context compaction for long multi-slice runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from agent_core.context_budget import estimate_tokens
from agent_core.models.slice_handoff import SliceHandoffSummary
from nimbusware_orchestrator.slice_handoff import handoff_markdown_capped

CompactionScope = Literal["all", "last_n"]


@dataclass(frozen=True)
class CompactionResult:
    summary: str
    tokens_before: int
    tokens_after: int
    kept_event_seq_range: tuple[int, int]
    handoff: SliceHandoffSummary
    merged_handoff_seqs: tuple[int, ...] = ()
    merged_handoff_count: int = 0


def campaign_compact_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_CAMPAIGN_COMPACT_ENABLED", default=True)


def _default_keep_recent_tokens() -> int:
    from nimbusware_env.env_flags import nimbusware_campaign_keep_recent_tokens

    return nimbusware_campaign_keep_recent_tokens()


def _default_reserve_tokens() -> int:
    from nimbusware_env.env_flags import nimbusware_campaign_reserve_tokens

    return nimbusware_campaign_reserve_tokens()


def reverted_compaction_ids(events: list[dict[str, Any]]) -> set[str]:
    """Compaction ids marked reverted via campaign.context.compaction.reverted events."""
    reverted: set[str] = set()
    for row in events:
        payload = row.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        if payload.get("stage_name") != "campaign.context.compaction.reverted":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        cid = meta.get("compaction_id")
        if isinstance(cid, str) and cid.strip():
            reverted.add(cid.strip())
    return reverted


def find_compaction_event(
    events: list[dict[str, Any]],
    compaction_id: str,
) -> dict[str, Any] | None:
    target = compaction_id.strip()
    if not target:
        return None
    for row in events:
        payload = row.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        if payload.get("stage_name") != "campaign.context.compacted":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        if str(meta.get("compaction_id") or "").strip() == target:
            return row
    return None


def _handoff_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in events:
        payload = row.get("payload") or {}
        if isinstance(payload, dict) and payload.get("stage_name") == "slice.handoff":
            rows.append(row)
    return rows


def compact_campaign_context(
    events: list[dict[str, Any]],
    *,
    keep_recent_tokens: int | None = None,
    reserve_tokens: int | None = None,
    scope: CompactionScope = "all",
    scope_n: int | None = None,
) -> CompactionResult | None:
    """Summarize older slice handoffs; keep recent verbatim within token budget."""
    if not campaign_compact_enabled():
        return None
    handoffs = _handoff_events(events)
    if scope == "last_n":
        n = max(1, int(scope_n or 1))
        handoffs = handoffs[-n:]
    if len(handoffs) < 3:
        return None

    keep = keep_recent_tokens if keep_recent_tokens is not None else _default_keep_recent_tokens()
    reserve = reserve_tokens if reserve_tokens is not None else _default_reserve_tokens()
    keep = max(1, keep - max(0, reserve))

    recent: list[dict[str, Any]] = []
    older: list[dict[str, Any]] = []
    token_budget = 0
    for row in reversed(handoffs):
        raw_meta = row.get("metadata")
        meta: dict[str, Any] = raw_meta if isinstance(raw_meta, dict) else {}
        summary_text = str(meta.get("handoff_summary") or "")
        tokens = estimate_tokens(summary_text)
        if token_budget + tokens <= keep:
            recent.insert(0, row)
            token_budget += tokens
        else:
            older.insert(0, row)

    if not older:
        return None

    reverted = reverted_compaction_ids(events)
    merged = _merge_handoffs(older, prior=_latest_compaction_prior(events, reverted=reverted))
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
    merged_seqs = tuple(
        int(r.get("store_seq") or r.get("seq") or 0)
        for r in older
        if int(r.get("store_seq") or r.get("seq") or 0) > 0
    )

    return CompactionResult(
        summary=compact_summary,
        tokens_before=tokens_before,
        tokens_after=tokens_after,
        kept_event_seq_range=kept_range,
        handoff=merged,
        merged_handoff_seqs=merged_seqs,
        merged_handoff_count=len(merged_seqs),
    )


def _latest_compaction_prior(
    events: list[dict[str, Any]],
    *,
    reverted: set[str] | None = None,
) -> SliceHandoffSummary | None:
    skip = reverted if reverted is not None else reverted_compaction_ids(events)
    prior: SliceHandoffSummary | None = None
    for row in events:
        payload = row.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        if payload.get("stage_name") != "campaign.context.compacted":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        cid = str(meta.get("compaction_id") or "").strip()
        if cid and cid in skip:
            continue
        handoff_raw = meta.get("slice_handoff")
        if isinstance(handoff_raw, dict):
            prior = SliceHandoffSummary.model_validate(handoff_raw)
            continue
        summary = meta.get("summary")
        if isinstance(summary, str) and summary.strip():
            prior = SliceHandoffSummary.parse_sections(summary)
    return prior


def _union_handoff_summaries(
    left: SliceHandoffSummary,
    right: SliceHandoffSummary,
) -> SliceHandoffSummary:
    return SliceHandoffSummary(
        goal=left.goal or right.goal,
        progress=tuple(dict.fromkeys((*left.progress, *right.progress))),
        key_decisions=tuple(dict.fromkeys((*left.key_decisions, *right.key_decisions))),
        next_steps=right.next_steps or left.next_steps,
        read_files=tuple(dict.fromkeys((*left.read_files, *right.read_files))),
        modified_files=tuple(dict.fromkeys((*left.modified_files, *right.modified_files))),
    )


def _merge_handoffs(
    rows: list[dict[str, Any]],
    *,
    prior: SliceHandoffSummary | None = None,
) -> SliceHandoffSummary:
    merged = prior
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
        merged = _union_handoff_summaries(merged, handoff)
    return merged or SliceHandoffSummary(goal="(compacted campaign context)")


def emit_compaction_revert_event(
    store: object,
    *,
    run_id: object,
    compaction_id: str,
    reverted_by: str,
    reason: str,
) -> None:
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
                "compaction_id": compaction_id.strip(),
                "reverted_by": reverted_by.strip() or "operator",
                "reason": reason.strip(),
            },
            payload=StageStartedPayload(
                stage_name="campaign.context.compaction.reverted",
                attempt=1,
            ),
        ),
    )


def maybe_emit_compaction_event(
    store: object,
    *,
    run_id: object,
    events: list[dict[str, Any]],
    keep_recent_tokens: int | None = None,
    reserve_tokens: int | None = None,
    compaction_trigger: str = "auto_handoff",
    scope: CompactionScope = "all",
    scope_n: int | None = None,
) -> CompactionResult | None:
    """Compact when enabled and append a campaign.context.compacted marker event."""
    result = compact_campaign_context(
        events,
        keep_recent_tokens=keep_recent_tokens,
        reserve_tokens=reserve_tokens,
        scope=scope,
        scope_n=scope_n,
    )
    if result is None:
        return None
    from datetime import datetime, timezone
    from uuid import uuid4

    from agent_core.models import EventType, StageStartedEvent, StageStartedPayload

    compaction_id = uuid4()
    store.append(  # type: ignore[attr-defined]
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,  # type: ignore[arg-type]
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "campaign_context_compacted": True,
                "compaction_id": str(compaction_id),
                "compaction_trigger": compaction_trigger,
                "summary": result.summary,
                "tokens_before": result.tokens_before,
                "tokens_after": result.tokens_after,
                "kept_event_seq_range": list(result.kept_event_seq_range),
                "merged_handoff_count": result.merged_handoff_count,
                "merged_handoff_seqs": list(result.merged_handoff_seqs),
                "slice_handoff": result.handoff.model_dump(mode="json"),
            },
            payload=StageStartedPayload(stage_name="campaign.context.compacted", attempt=1),
        ),
    )
    return result
