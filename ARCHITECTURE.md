# Nimbusware architecture

One-page map of packages, data flow, and auth. Normative product contract: [hermes-orchestrator-local-plan.md](hermes-orchestrator-local-plan.md). Sprint board: [PLAN_GAP.md](PLAN_GAP.md).

## Layer diagram

```text
┌─────────────────────────────────────────────────────────────┐
│  UI (Streamlit)                                              │
│  nimbusware_maker (user)    nimbusware_console (admin/dev)   │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP /v1
┌────────────────────────────▼────────────────────────────────┐
│  nimbusware_api (FastAPI)                                    │
│  UserDep / AdminDep · OpenAPI user/admin tags                │
└─────┬──────────────────┬──────────────────┬─────────────────┘
      │                  │                  │
      ▼                  ▼                  ▼
 hermes_orchestrator  nimbusware_projections  nimbusware_iam
 (RunOrchestrator)    (timeline read models)   (Enterprise keys)
      │
      ▼
 hermes_store (append-only events)  +  nimbusware_config (YAML→Postgres)
      │
      ▼
 PostgreSQL (or InMemoryEventStore without NIMBUSWARE_DATABASE_URL)
```

## Packages

| Package | Role |
|---------|------|
| `agent_core` | Event models, validation |
| `hermes_store` | Event store (Postgres / memory) |
| `hermes_orchestrator` | Pipeline, critics, gates, micro-slice, preflight |
| `hermes_memory` | Repo-scoped retrieval index (+ fleet on Enterprise) |
| `hermes_extensions` | Personas, bundles, escalation helpers |
| `hermes_executor` | Role-gated outbound HTTP |
| `hermes_agent_tools` | Allowlisted tools for slice implement agent mode |
| `nimbusware_config` | Versioned config documents + materializer |
| `nimbusware_projections` | Pure functions: events → timeline summaries |
| `nimbusware_api` | REST control plane |
| `nimbusware_client` | Shared HTTP client for Maker + Admin UIs |
| `nimbusware_iam` | Enterprise tenants + API keys (`maker_user` / `maker_admin`) |
| `nimbusware_maker` | User product UI |
| `nimbusware_console` | Admin Console (config, fleet, deep timeline) |
| `nimbusware_env` | Edition gate, desktop launchers, dotenv, `env_flags`, admin token guards |

## Editions

| Edition | Auth |
|---------|------|
| **Individual** (default) | User routes open on localhost; admin routes need `X-Nimbusware-Admin-Token` |
| **Enterprise** | All routes need `X-Nimbusware-Api-Key`; scopes `maker_user` / `maker_admin` |

## Import rules (enforced)

- `hermes_extensions` must not import `hermes_orchestrator` at module level (`tests/unit/test_import_graph.py`).
- `hermes_orchestrator` must not import `nimbusware_api` (Lane R-C — use `nimbusware_projections`).
- Legacy `packages/hermes_{api,console,config,env}/` shims removed (Lane R-B).

## Refactor lane

See [PLAN_GAP.md § Lane R](PLAN_GAP.md#lane-r--maintainability-refactor-fo400fo407) for console decomposition and coverage gates.

Local CI mirror: `./scripts/ci_check.sh` or `scripts/ci_check.ps1` (Ruff, Mypy, Bandit, pytest with `--cov-fail-under=60`).

Module size guards: `tests/unit/test_console_module_size.py` (400 lines), `tests/unit/test_package_module_size.py` (orchestrator/API/memory), `tests/unit/test_module_integrity.py` (anti-gutted facades).

Display packages use explicit re-exports (`scripts/explicit_star_imports.py`); avoid repo-wide `ruff check --fix`, which strips re-export imports.
