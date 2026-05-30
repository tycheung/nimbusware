# Nimbusware / Hermes architecture

## Layers

| Layer | Package | Role |
|-------|---------|------|
| Events | `agent_core` | Pydantic event models and validation |
| Persistence | `hermes_store` | Append-only Postgres / in-memory store |
| Orchestration | `hermes_orchestrator` | Run pipeline, critics, gates, dispatch |
| Projections | `nimbusware_projections` | Shared timeline/list builders and field metadata |
| API | `nimbusware_api` | FastAPI `/v1` control plane |
| Console | `nimbusware_console` | Streamlit operator UI |
| Config | `nimbusware_config` | Versioned Postgres documents + materializer |
| Memory | `hermes_memory` | Retrieval index (repo or fleet scope) |
| IAM | `nimbusware_iam` | Enterprise tenancy and API keys |
| Editions | `nimbusware_env` | Individual vs enterprise gate |

## Facade pattern

External contracts stay stable while internals split into packages:

- `nimbusware_api.facade.build_v1_router()` — HTTP routes
- `hermes_orchestrator.pipeline` — `RunOrchestrator` (implementation in `_pipeline/`)
- `nimbusware_console.main.render_main()` — console sections
- `nimbusware_console.pages.run_detail/` — run detail UI split into summary, timeline, findings, actions panels
- `nimbusware_projections` — shared read-model builders consumed by API and console

## Data flow

```text
Operator / API
    → RunOrchestrator (pipeline)
    → EventStore append
    → read_models / projections
    → HTTP JSON or Streamlit display
```

## Edition gate

`NIMBUSWARE_EDITION=individual|enterprise` controls IAM, fleet memory, Redis workers, and enterprise-only routes (404 on Individual).

See [adr/001-event-sourced-runs.md](adr/001-event-sourced-runs.md) and [adr/002-edition-gate.md](adr/002-edition-gate.md).
