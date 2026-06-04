# Nimbusware architecture

**Nimbusware** is this codebase (local-first platform: `nimbusware_*`, `NIMBUSWARE_*`). **Hermes** is the online agentic system; integration lives in `hermes_*` packages and `HERMES_*` env (see [ARCHITECTURE.md](../ARCHITECTURE.md#nomenclature)).

## Layers

| Layer | Package | Role |
|-------|---------|------|
| Events | `agent_core` | Pydantic event models and validation |
| Persistence | `hermes_store` | Append-only Postgres / in-memory store |
| Orchestration | `hermes_orchestrator` | Run pipeline, critics, gates, dispatch (`runtime_bootstrap` wires API + worker) |
| Projections | `nimbusware_projections` | Shared timeline/list builders and field metadata |
| API | `nimbusware_api` | FastAPI `/v1` control plane |
| Maker web | `nimbusware_maker_web` | Alpine operator UI at `/v1/maker/app/` |
| Maker logic | `nimbusware_maker` | Approval state machine, slice workflow helpers |
| Admin web | `nimbusware_admin_ui` | Preact SPA at `/v1/admin/app/` |
| Admin services | `nimbusware_console` | Display modules + BFF-backed panels (no Streamlit) |
| Config | `nimbusware_config` | Versioned Postgres documents + materializer |
| Memory | `hermes_memory` | Retrieval index (repo or fleet scope) |
| IAM | `nimbusware_iam` | Enterprise tenancy and API keys |
| Editions | `nimbusware_env` | Individual vs enterprise gate |
| Hardware | `nimbusware_hw` | Probe, governor, pressure, catalog fit; `/v1/platform/hardware` and `/v1/platform/models/*` |

## Facade pattern

External contracts stay stable while internals split into packages:

- `nimbusware_api.facade.build_v1_router()` — HTTP routes
- `hermes_orchestrator.pipeline` — `RunOrchestrator` (implementation in `_pipeline/`)
- `nimbusware_console` display modules — consumed by Admin BFF routes
- `nimbusware_projections` — shared read-model builders consumed by API and Admin

## Data flow

```text
Operator (Maker or Admin web)
    → HTTP /v1 JSON
    → RunOrchestrator (pipeline) on lifecycle actions
    → EventStore append
    → projections / read_models
    → SSE or poll in web UI
```

## Edition gate

`NIMBUSWARE_EDITION=individual|enterprise` controls IAM, fleet memory, Redis workers, and enterprise-only routes (404 on Individual).

See [adr/001-event-sourced-runs.md](adr/001-event-sourced-runs.md) through [adr/005-request-correlation-id.md](adr/005-request-correlation-id.md).

## Quality gates

See [tests/README.md](../tests/README.md) and `scripts/ci_check.ps1`.
