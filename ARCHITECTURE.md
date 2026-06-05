# Nimbusware architecture

## Nomenclature

| Name | Meaning |
|------|---------|
| **Nimbusware** | This repository and product: local-first platform (API, Maker, Admin Console, config, IAM). Use `NIMBUSWARE_*` env vars and `nimbusware_*` packages. |
| **Hermes** | The **online agentic system** (adversarial multi-role runs, critics, gates, verifiers). This codebase integrates it locally via `hermes_*` packages and `HERMES_*` env vars — not a second product name for Nimbusware. |

Legacy checkout paths (e.g. `D:\Hermes`) and artifact dirs (`.hermes/`) are historical; prefer **Nimbusware** in user-facing text.

One-page map of packages, data flow, and auth. Normative Hermes agent contract: gitignored `hermes-orchestrator-local-plan.md` (repo root). Maturity backlog: gitignored `plan_gap.md`. ADR index: [docs/architecture.md](docs/architecture.md).

## Layer diagram

```text
┌─────────────────────────────────────────────────────────────┐
│  UI (web + pywebview desktop)                                │
│  nimbusware_maker_web (/v1/maker/app)  nimbusware_admin_ui   │
│  nimbusware_console (services + display modules for Admin BFF) │
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
| `hermes_orchestrator` | Pipeline, critics, gates, micro-slice (`slice.e2e`, budget presets), fleet analytics, blast-radius preview, audit export |
| `hermes_memory` | Repo-scoped retrieval index (+ fleet on Enterprise) |
| `hermes_extensions` | Personas, bundles, escalation helpers |
| `hermes_executor` | Role-gated outbound HTTP |
| `hermes_research` | Research briefs, stitch transplant stages, stitch read models and outcome stats |
| `hermes_agent_tools` | Allowlisted tools; `filesystem_jail` + sandbox backends — `none`/`stub`/`docker` (Individual); `kubernetes`/`e2b` fleet sandboxes; per-slice risk caps |
| `nimbusware_config` | Versioned config documents + materializer |
| `nimbusware_projections` | Events → timeline, maker-progress, theater (+ export, slice gate lines), research briefs |
| `nimbusware_maker_web` | Alpine Maker web app (tabs, SSE progress) at `/v1/maker/app` |
| `nimbusware_admin_ui` | Preact Admin SPA at `/v1/admin/app` (Enterprise fleet at `/fleet`) |
| `nimbusware_mcp` | Stdio MCP IDE bridge (`nimbusware-mcp`; see `docs/ide-bridge.md`) |
| `nimbusware_api` | REST control plane |
| `nimbusware_client` | Shared HTTP client for Maker + Admin UIs |
| `nimbusware_iam` | Enterprise tenants, API keys, IAM action log for audit export |
| `nimbusware_maker` | Maker server logic — projects, intent, approval/revert (`services/` + `slice_workflow/`) |
| `nimbusware_console` | Admin display helpers + enterprise fleet formatters; BFF tables via `routes/admin_ui_bff.py` |
| `nimbusware_env` | Edition gate, OIDC config, desktop launchers, dotenv, `env_flags`, admin token guards |
| `nimbusware_hw` | Probe, governor, pressure, catalog fit; local + Enterprise SSH remote probe; `/v1/platform/hardware`, `/v1/platform/hardware/fleet`, `/v1/platform/models/*` |

## Editions

| Edition | Auth |
|---------|------|
| **Individual** (default) | User routes open on localhost; admin routes need `X-Nimbusware-Admin-Token` |
| **Enterprise** | All routes need `X-Nimbusware-Api-Key`; scopes `maker_user` / `maker_admin` |

## Data flow

1. **Create** — Maker `POST /v1/runs` (or Admin lifecycle) appends `run.created` via `RunOrchestrator` → `hermes_store`.
2. **Pipeline** — Orchestrator mixins append stage events; projections rebuild timelines and maker-progress without API imports from orchestrator.
3. **Read** — HTTP handlers use `nimbusware_projections` / `read_models/`; Admin BFF routes call `nimbusware_console` display formatters.
4. **Maker loop** — Pending slices, research approve/reject, and stitch summary are read models over the same event log (`nimbusware_maker` + maker web tabs).

## Auth (request path)

| Surface | Header / cookie |
|---------|------------------|
| Maker user routes | Open on loopback (Individual); `X-Nimbusware-Api-Key` (`maker_user`) on Enterprise |
| Admin API routes | `X-Nimbusware-Admin-Token` (Individual); `maker_admin` key (Enterprise) |
| Admin SPA SSO | Optional OIDC session cookie for shell only — API calls still need admin token / API key ([docs/deploy/oidc.md](docs/deploy/oidc.md)) |

## Import rules (enforced)

- `hermes_extensions` must not import `hermes_orchestrator` at module level (`tests/unit/test_import_graph.py`).
- `hermes_orchestrator` must not import `nimbusware_api` (Lane R-C — use `nimbusware_projections`).
- Legacy `packages/hermes_{api,console,config,env}/` shims removed (Lane R-B).

## Architecture decision records

See [docs/architecture.md](docs/architecture.md) for ADR links (event store, edition gate, projections, logging, correlation IDs).

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

**Coverage:** CI enforces `--cov-fail-under=75` on the default unit subset. Per-package floors (≥85%): `agent_core`, `hermes_store`, `hermes_executor`, `nimbusware_config`, `nimbusware_projections` via `scripts/coverage_package_floors.py`. Web static assets (`nimbusware_maker_web`, `nimbusware_admin_ui`) and desktop launcher modules are omitted from the denominator (`pyproject.toml`).

**Typing:** Global mypy `strict = true`. CI checks paths from `scripts/mypy_ci_targets.py`:

| Tranche | Packages / paths |
|---------|------------------|
| B | `nimbusware_projections`, `nimbusware_client`, `hermes_agent_tools` |
| C | `agent_core`, `hermes_store`, `nimbusware_config`, `hermes_executor`, `hermes_extensions`, `hermes_memory`, `nimbusware_iam`, `nimbusware_env` |
| D | `nimbusware_api/read_models`, `facade`, `deps`, `routes/enterprise`, `routes/personas_helpers` |
| E | Orchestrator islands: orchestrator root modules plus full `_pipeline/*` (including `dev_factory`, `compose`, `protocol_hosts`, `pipeline_scraper`); probation/fast-slice workflow metadata on `run.created` (see `scripts/mypy_ci_targets.py` `_TRANCHE_E`) |
| API pilot | `routes/ollama`, `schemas/ollama`, `errors` |
| UI | Full `nimbusware_console` and `nimbusware_maker` under narrowed ignore list; `services/*` strict |

All `_pipeline` modules are strict-checked mypy islands (including `dev_factory`); `protocol_hosts.py` documents host protocols for pipeline mixins. API lifespan and the run worker share `hermes_orchestrator.runtime_bootstrap.build_runtime_orchestrator`.

**Hardware events:** `POST /v1/platform/hardware/rescan` accepts optional `emit_event` + `run_id` to append `hardware.profile.detected`. Memory index rebuild at run start defers when `sample_pressure` is not `ok` (governor RAM cap). Stitch transplant pass rate: `GET /v1/platform/analytics/stitch-outcomes` (Admin Console panel under Config → Workflows).

**PEP 561:** Core libraries ship `py.typed` markers (`agent_core`, `hermes_store`, `hermes_orchestrator`, `nimbusware_config`, `nimbusware_projections`, `hermes_executor`, `nimbusware_iam`, `nimbusware_env`, plus UI/API packages).

**CI parity:** `ci_check.*` runs ruff check + **blocking** format, mypy (targets above), bandit (`pyproject.toml`), pip-audit, package coverage floors, pytest @ 75%.

**Size guards:** `test_console_module_size.py` (400 lines), `test_package_module_size.py` (450 lines), `test_module_integrity.py` (anti-gutted facades), `test_pipeline_helpers_exports.py` (orchestrator mixin surface).
