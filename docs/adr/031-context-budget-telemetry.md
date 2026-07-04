# ADR 031: Persisted context budget telemetry

## Status

Accepted (2026-07)

## Context

Provider chats already record in-process token counters (`agent_core/token_telemetry.py`).
Operators need durable, run-scoped samples for Progress budget chips and fleet dashboards
without emitting an event on every LLM call (which would bloat the event store).

## Decision

1. **Event type** — append `context.budget.sampled` with payload
   `{ provider, stage_name, tokens_in, tokens_out, cache_read, cache_write }`.
2. **Rate limit** — at most one sample per run every 30 seconds (monotonic clock keyed by `run_id`).
3. **Binding** — `bind_budget_sample_context(store, run_id)` sets context vars before stage
   execution (`role_execute`, slice executor). Provider telemetry calls
   `maybe_emit_context_budget_sample` after each chat; no-op when store is unbound.
4. **Read path** — `projections/builders/context_budget.py` aggregates samples from run events;
   `GET /v1/runs/{id}/context_budget` remains advisory.

In-process counters continue for hot-path diagnostics; persisted samples are for UI and audit.

## Consequences

- Postgres schema CHECK list must include `context.budget.sampled` alongside code-defined types.
- Per-run rate limiting (30s) is sufficient for budget trend chips; not per-stage.
- Tests without a real store (fake orchestrators) skip emission via the store guard.

## Alternatives considered

| Option | Rejected because |
|--------|------------------|
| Event per LLM call | Event store growth on long JIT loops |
| Metrics-only (no events) | Breaks event-sourced projections and run audit export |
| Postgres side table | Duplicates event-sourced read model pattern |
