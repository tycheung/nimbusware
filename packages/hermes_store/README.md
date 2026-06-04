# hermes_store

Append-only event store for Hermes agent runs (via Nimbusware): Postgres when `NIMBUSWARE_DATABASE_URL` is set, otherwise in-memory for local development.

## Layout

| Module | Role |
|--------|------|
| `postgres.py` | SQL-backed append + replay |
| `memory.py` | `InMemoryEventStore` for tests and offline use |
| `schema/postgres.sql` | Canonical DDL + `event_store_type_allowed` (incl. `research.brief.*`) |
| `migrations/README.md` | Greenfield apply; notes for extending the event CHECK on live DBs |

## Consumers

`hermes_orchestrator` appends pipeline events; `nimbusware_api` and `nimbusware_projections` read timelines and summaries.

Ships PEP 561 marker (`py.typed`). Per-package coverage floor: ≥85% in CI.

Normative Hermes contract: gitignored `hermes-orchestrator-local-plan.md` at repo root.
