# Nimbusware architecture

One-page map of packages, data flow, and auth. Normative product contract: [hermes-orchestrator-local-plan.md](hermes-orchestrator-local-plan.md). Local maturity ledger: [PLAN_GAP.md](PLAN_GAP.md) (gitignored).

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

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) for setup, CI, and production secrets. Day-to-day workflow:

| Step | Command / guard |
|------|-----------------|
| Local CI | `./scripts/ci_check.ps1` or `scripts/ci_check.sh` |
| After display package splits | `poetry run python scripts/explicit_star_imports.py` |
| After package `__init__` export changes | `poetry run python scripts/sync_display_facade.py` |
| Run detail import barrels | `poetry run python scripts/explicit_run_detail_imports.py` |
| Facade contract | `tests/unit/test_display_facade_exports.py` |
| Module splits (orchestrator/API/events) | `scripts/split_oversized_modules.py` (one-off; prefer manual follow-up) |

**Do not** run repo-wide `ruff check --fix` — it strips explicit re-export imports.

**Coverage:** CI enforces `--cov-fail-under=75` on the default unit subset. Per-package floors (≥85%): `agent_core`, `hermes_store`, `hermes_executor`, `nimbusware_config`, `nimbusware_projections` via `scripts/coverage_package_floors.py`. Streamlit `pages/**` and Maker `ui/**` are omitted from the denominator (`pyproject.toml`).

**Typing:** Global mypy `strict = true`. CI checks paths from `scripts/mypy_ci_targets.py`:

| Tranche | Packages / paths |
|---------|------------------|
| B | `nimbusware_projections`, `nimbusware_client`, `hermes_agent_tools` |
| C | `agent_core`, `hermes_store`, `nimbusware_config`, `hermes_executor`, `hermes_extensions`, `hermes_memory`, `nimbusware_iam`, `nimbusware_env` |
| D | `nimbusware_api/read_models`, `facade`, `deps`, `routes/enterprise`, `routes/personas_helpers` |
| E | Orchestrator islands: `ollama_manage`, `ollama_user_policy`, `preflight`, `merge`, `workflow_profiles`, `_pipeline/create_run` (mypy pilot) |
| API pilot | `routes/ollama`, `schemas/ollama`, `errors` |
| UI | Full `nimbusware_console` and `nimbusware_maker` under narrowed ignore list; `services/*` strict |

`hermes_orchestrator._pipeline.*` mixins stay `ignore_errors = true` except `_pipeline/create_run` (strict pilot). API lifespan and the run worker share `hermes_orchestrator.runtime_bootstrap.build_runtime_orchestrator`.

**PEP 561:** Core libraries ship `py.typed` markers (`agent_core`, `hermes_store`, `hermes_orchestrator`, `nimbusware_config`, `nimbusware_projections`, `hermes_executor`, `nimbusware_iam`, `nimbusware_env`, plus UI/API packages).

**CI parity:** `ci_check.*` runs ruff check + **blocking** format, mypy (targets above), bandit (`pyproject.toml`), pip-audit, package coverage floors, pytest @ 75%.

**Size guards:** `test_console_module_size.py` (400 lines), `test_package_module_size.py` (450 lines), `test_module_integrity.py` (anti-gutted facades), `test_pipeline_helpers_exports.py` (orchestrator mixin surface).
