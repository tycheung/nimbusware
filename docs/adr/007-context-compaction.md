# ADR 007: Campaign context compaction

## Status

Accepted (2026-06)

## Context

Long campaigns accumulate slice handoff events. Planner prompts would grow linearly
without summarizing older handoffs. Raw events remain authoritative in the event store.

## Decision

- `compact_campaign_context` in `orchestrator.context_compaction` walks
  handoff events backward, keeps recent summaries within `NIMBUSWARE_CAMPAIGN_KEEP_RECENT_TOKENS`
  (minus reserve), and merges older `SliceHandoffSummary` blobs deterministically.
- Compaction emits `stage.started` with `stage_name=campaign.context.compacted` and
  metadata `{ summary, tokens_before, tokens_after, kept_event_seq_range }`.
- Triggered after each `slice.handoff` when `NIMBUSWARE_CAMPAIGN_COMPACT_ENABLED` and
  at least three handoffs exist.

## Consequences

- Planner can read latest compaction summary from run events (future campaign driver).
- Hardware governor can influence default keep-recent window via cached profile context.
- Re-compaction reads the latest `campaign.context.compacted` marker and merges new
  older handoffs onto that prior summary via `SliceHandoffSummary.parse_sections`.
- `<read-files>` and `<modified-files>` lists grow monotonically (union/dedupe) across
  successive compactions so file provenance is not dropped.
