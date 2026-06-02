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
| `nimbusware_maker` | User product UI (`ui/` Streamlit; `services/` testable HTTP helpers) |
| `nimbusware_console` | Admin Console (config, fleet, deep timeline; `services/` HTTP helpers) |
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

## Refactor playbook

See [PLAN_GAP.md § Lane R](PLAN_GAP.md#lane-r--maintainability-refactor-fo400fo407) for the refactor program. **Lane T (fo520–fo545)** shipped: UI `services/` plane, mypy ratchet (API strict, `_pipeline` mixins ignored), `run_detail/_imports` star facade, **72%** CI coverage floor, async Ollama pull jobs. Day-to-day workflow:

| Step | Command / guard |
|------|-----------------|
| Local CI | `./scripts/ci_check.ps1` or `scripts/ci_check.sh` |
| After display package splits | `poetry run python scripts/explicit_star_imports.py` |
| After package `__init__` export changes | `poetry run python scripts/sync_display_facade.py` |
| Run detail import barrels | `poetry run python scripts/explicit_run_detail_imports.py` |
| Facade contract | `tests/unit/test_display_facade_exports.py` |
| Module splits (orchestrator/API/events) | `scripts/split_oversized_modules.py` (one-off; prefer manual follow-up) |

**Do not** run repo-wide `ruff check --fix` — it strips explicit re-export imports.

**Coverage:** CI enforces `--cov-fail-under=72` on the default unit subset (library code; Streamlit `pages/**` and `ui/**` omitted per `pyproject.toml`; `services/` packages stay in the denominator).

**Typing (Lane V1 / W0):** `nimbusware_{console,maker}.services.*` are strict mypy islands (`test_mypy_services_surface.py`); UI packages remain ignored except `services/`. Pre-commit and GitHub CI run the **same** mypy scope (services only — fo701).

**CI parity (Lane W0):** `ci_check.*` runs ruff, mypy (services), bandit, `pip-audit`, `coverage_package_floors.py`, then pytest at the coverage floor.

**Size guards:** `test_console_module_size.py` (400 lines), `test_package_module_size.py` (450 lines), `test_module_integrity.py` (anti-gutted facades), `test_pipeline_helpers_exports.py` (orchestrator mixin surface).
