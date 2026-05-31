# nimbusware_config

Versioned YAML config documents (workflows, personas, bundles) with Postgres materializer and optimistic concurrency for Admin Console edits.

## Layout

| Area | Role |
|------|------|
| `documents/` | Typed config document models |
| `materializer.py` | YAML ↔ Postgres sync |
| `store.py` | Read/write with expected-version checks |

## Consumers

`nimbusware_api` admin routes, `nimbusware_console` config tooling, `hermes_orchestrator` workflow merge at run start.

Normative contract: [hermes-orchestrator-local-plan.md](../../hermes-orchestrator-local-plan.md).
