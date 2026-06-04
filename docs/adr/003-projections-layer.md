# ADR 003: Shared projections layer

## Status

Accepted (2026-05)

## Context

Timeline summaries and field metadata were duplicated between `nimbusware_api.read_models` and console display modules. Divergence caused console/API parity bugs and made operator exports hard to keep consistent.

## Decision

Introduce `nimbusware_projections` with:

- `builders/` — pure functions over normalized event dicts (no HTTP or UI framework)
- `fields/` — row keys and human-facing display field order shared by API examples and console tables

API `read_models/*` modules become thin shims that delegate to projections. Console display modules import field metadata (for example `RUN_ESCALATED_DISPLAY_FIELDS`) from projections rather than redefining tuples.

## Consequences

- Parity tests in `tests/unit/test_projection_parity.py` assert API shims match builders.
- New timeline domains should land in projections first, then wire API and console.
- `stage_timeline` builders may still call orchestrator helpers where live matrix logic lives; extract further when those helpers stabilize.

## References

- `packages/nimbusware_projections/`
- [ARCHITECTURE.md](../../ARCHITECTURE.md) (projections in package map)
- [docs/architecture.md](../architecture.md) (ADR index)
