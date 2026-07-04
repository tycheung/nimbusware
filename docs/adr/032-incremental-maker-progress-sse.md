# ADR 032: Incremental Maker Progress SSE

## Status

Accepted (2026-07)

## Context

Maker Progress polls run events to render slice status. Re-fetching and re-projecting the
full event timeline on every poll scales poorly for long campaigns (hundreds of events).
The client only needs new rows plus changed projection fields.

## Decision

1. **Store API** — `EventStore.list_run_events_since(run_id, after_seq)` returns rows with
   `store_seq > after_seq` (implemented on in-memory and Postgres stores).
2. **Stream route** — `GET /v1/runs/{id}/maker-progress/stream`:
   - Seeds from cached rows (optionally filtered by `cursor` query param).
   - Poll loop tail-fetches via `list_run_events_since`, appends to an in-memory buffer,
     and re-runs `maker_progress_from_events` on the accumulated set.
3. **SSE event types**:
   - `progress` — full projection snapshot (initial connect or when delta is empty).
   - `progress_delta` — shallow diff of top-level projection keys that changed.
   - `event` — lightweight `{ store_seq, event_type }` for theater/debug consumers.
   - `heartbeat` / `done` — liveness and terminal run detection.
4. **Client** — `maker_web/static/js/tabs/progress.js` merges `progress_delta` into the
   cached projection instead of replacing the entire DOM state.

Full event history remains in the store; the stream handler maintains a session-local buffer.

## Consequences

- SSE sessions are stateful server-side for the duration of the connection (accumulated rows).
- Reconnect with `cursor=last_seq` avoids replaying events already seen.
- Projection parity tests must cover delta merge semantics if projection shape changes.

## Alternatives considered

| Option | Rejected because |
|--------|------------------|
| Full replay each poll | O(n) per tick on long runs |
| Server-side materialized progress table | Extra write path; events already authoritative |
| WebSocket push from orchestrator | Heavier infra; polling + tail fetch sufficient for Progress |
