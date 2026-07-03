# ADR 001: Event-sourced runs

## Status

Accepted

## Context

Run lifecycle state must be auditable, replayable, and consistent across API, workers, and console.

## Decision

Persist all run state as an append-only event log in `store`. HTTP handlers and `RunOrchestrator` append typed events from `agent_core.models`; read paths project timelines via `projections` and `api.read_models`.

## Consequences

- No mutable run row — summaries are derived.
- Replay and integration tests can assert on event sequences.
- Timeline enrichment logic lives in projections, not handlers.
