# hermes_store

Append-only event store for Hermes agent runs (via Nimbusware): Postgres when `NIMBUSWARE_DATABASE_URL` is set, otherwise in-memory for local development.

## Layout

| Module | Role |
|--------|------|
| `postgres.py` | SQL-backed append + replay |
| `memory.py` | `InMemoryEventStore` for tests and offline use |
| `schema/postgres.sql` | Canonical DDL (applied via `scripts/apply_event_store.sh`) |

## Consumers

`hermes_orchestrator` appends pipeline events; `nimbusware_api` and `nimbusware_projections` read timelines and summaries.

Ships PEP 561 marker (`py.typed`). Per-package coverage floor: ≥85% in CI.

Normative contract: [hermes-orchestrator-local-plan.md](../../hermes-orchestrator-local-plan.md).
