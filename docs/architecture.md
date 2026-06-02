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
| Maker | `nimbusware_maker` | Streamlit product UI — `GET/POST/PATCH /projects`, maker progress, slice approval/revert |
| Admin Console | `nimbusware_console` | Streamlit ops/dev control plane |
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

See [adr/001-event-sourced-runs.md](adr/001-event-sourced-runs.md) through [adr/005-request-correlation-id.md](adr/005-request-correlation-id.md).

## Quality gates

Local CI parity: `scripts/ci_check.ps1` / `ci_check.sh` — ruff check + format, mypy (`scripts/mypy_ci_targets.py` tranches B–E + UI), bandit, pip-audit, pytest @ 75% + per-package floors (see [CONTRIBUTING.md](../CONTRIBUTING.md)).

Mypy tranches (CI-enforced): B = projections/client/agent_tools; C = core libs; D = API read layer + typed `deps.py`; E = orchestrator leaf modules + `_pipeline/create_run` pilot; API pilot (ollama routes/schemas, errors). UI packages checked under narrowed ignore list; other `_pipeline.*` mixins excluded.

Core libraries ship PEP 561 `py.typed` markers.

## Projections map

| Domain | Builder module | Field metadata |
|--------|----------------|----------------|
| Integrator gate | `builders/integrator_gate.py` | `fields/integrator_gate.py` |
| Security scan on verify | `builders/security_scan.py` | `fields/security_scan.py` |
| Agent evaluator | `builders/agent_evaluator.py` | `fields/agent_evaluator.py` |
| Self-refinement | `builders/self_refinement.py` | `fields/self_refinement.py` |
| Universal critique | `builders/universal_critique.py` | (inline stage keys) |
| Run escalated | `builders/run_escalated.py` | `fields/run_escalated.py` |
| Scraper fetch | `builders/scraper_fetch.py` | `fields/scraper_fetch.py` |
| Persona assignment | `builders/persona_assignment.py` | (from `run.created` metadata) |
| Stage graph / parallel writers / critic matrix | `builders/stage_timeline.py` | (orchestrator-backed) |

API shims live under `nimbusware_api/read_models/`. Console tables import `*_DISPLAY_FIELDS` or call the same builders via timeline JSON.
