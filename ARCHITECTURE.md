# Nimbusware architecture

## Nomenclature

| Name | Meaning |
|------|---------|
| **Nimbusware** | This repository and product: local-first adversarial agent platform (API, Maker, Admin Console, orchestrator, event store, config, IAM). Use `NIMBUSWARE_*` env vars and `nimbusware_*` packages. |

One-page map of packages, data flow, and auth. Normative Nimbusware agent contract: gitignored `nimbusware-orchestrator-local-plan.md` (repo root). Maturity backlog: gitignored `plan_gap.md`. ADR index: [docs/architecture.md](docs/architecture.md).

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
 nimbusware_orchestrator  nimbusware_projections  nimbusware_iam
 (RunOrchestrator)    (timeline read models)   (Enterprise keys)
      │
      ▼
 nimbusware_store (append-only events)  +  nimbusware_config (YAML→Postgres)
      │
      ▼
 PostgreSQL (or InMemoryEventStore without NIMBUSWARE_DATABASE_URL)
```

## Packages

| Package | Role |
|---------|------|
| `agent_core` | Event models, `context_budget`, slice handoff models |
| `nimbusware_store` | Event store (Postgres / memory) |
| `nimbusware_orchestrator` | Pipeline, critics, gates, micro-slice (`slice.e2e`, budget presets), **campaign driver** (backlog → one slice/tick → completion), maintenance refactor/architecture passes, `role_execute` dispatcher, fleet analytics, blast-radius preview, audit export |
| `nimbusware_memory` | Repo-scoped retrieval index (+ fleet on Enterprise) |
| `nimbusware_extensions` | Personas, bundles, escalation helpers |
| `nimbusware_executor` | Role-gated outbound HTTP |
| `nimbusware_research` | Research briefs, stitch transplant stages, stitch read models and outcome stats |
| `nimbusware_agent_tools` | JIT `agent_loop`, dual `ToolResult` output, tool allowlist, stable prompt file; jail + sandbox + risk caps |
| `nimbusware_config` | Versioned config documents + materializer |
| `nimbusware_projections` | Events → timeline, maker-progress, theater, context budget, agent-tool prune (+ export, research briefs) |
| `nimbusware_maker_web` | Alpine Maker web app (tabs, SSE progress) at `/v1/maker/app` |
| `nimbusware_admin_ui` | Preact Admin SPA at `/v1/admin/app` (Enterprise fleet at `/fleet`) |
| `nimbusware_mcp` | Stdio MCP IDE bridge (`nimbusware-mcp`; run status, theater, pending slices, campaign pause/resume; see `docs/ide-bridge.md`) |
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

1. **Create** — Maker `POST /v1/runs` (or Admin lifecycle) appends `run.created` via `RunOrchestrator` → `nimbusware_store`.
2. **Pipeline** — Orchestrator mixins append stage events; projections rebuild timelines and maker-progress from the event log.
3. **Read** — Campaign/backlog row parsers live in `agent_core.read.campaign` (shared by orchestrator and projections). HTTP handlers use `nimbusware_projections` / `read_models/`; Admin BFF routes call `nimbusware_console` display formatters.
4. **Maker loop** — Pending slices, research approve/reject, stitch summary, and launch readiness scorecards are read models over the same event log (`nimbusware_maker` + maker web tabs).

## Auth (request path)

| Surface | Header / cookie |
|---------|------------------|
| Maker user routes | Open on loopback (Individual); `X-Nimbusware-Api-Key` (`maker_user`) on Enterprise |
| Admin API routes | `X-Nimbusware-Admin-Token` (Individual); `maker_admin` key (Enterprise) |
| Admin SPA SSO | Optional OIDC session cookie for shell only — API calls still need admin token / API key ([docs/deploy/oidc.md](docs/deploy/oidc.md)) |

## Import rules (enforced)

- `nimbusware_extensions` must not import `nimbusware_orchestrator` at module level (`tests/unit/test_import_graph.py`).
- `nimbusware_orchestrator` must not import `nimbusware_api` (Lane R-C — use `nimbusware_projections`).
- `nimbusware_projections` must not import `nimbusware_orchestrator` at module level except legacy allowlist (`stage_timeline.py`, `universal_critique.py`).
- Legacy `packages/nimbusware_{api,console,config,env}/` shims removed (Lane R-B).

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

**Coverage:** CI enforces `--cov-fail-under=75` on the default unit subset. Per-package floors (≥85%): `agent_core`, `nimbusware_store`, `nimbusware_executor`, `nimbusware_config`, `nimbusware_projections` via `scripts/coverage_package_floors.py`. Web static assets (`nimbusware_maker_web`, `nimbusware_admin_ui`) and desktop launcher modules are omitted from the denominator (`pyproject.toml`).

**Typing:** Global mypy `strict = true`. CI checks paths from `scripts/mypy_ci_targets.py`:

| Tranche | Packages / paths |
|---------|------------------|
| B | `nimbusware_projections`, `nimbusware_client`, `nimbusware_agent_tools` |
| C | `agent_core`, `nimbusware_store`, `nimbusware_config`, `nimbusware_executor`, `nimbusware_extensions`, `nimbusware_memory`, `nimbusware_iam`, `nimbusware_env` |
| D | `nimbusware_api/read_models`, `facade`, `deps`, `routes/enterprise`, `routes/personas_helpers` |
| E | Orchestrator islands: orchestrator root modules plus full `_pipeline/*` (including `dev_factory`, `compose`, `protocol_hosts`, `pipeline_scraper`); probation/fast-slice workflow metadata on `run.created` (see `scripts/mypy_ci_targets.py` `_TRANCHE_E`) |
| API pilot | `routes/ollama`, `schemas/ollama`, `errors` |
| UI | Full `nimbusware_console` and `nimbusware_maker` under narrowed ignore list; `services/*` strict |

All `_pipeline` modules are strict-checked mypy islands (including `dev_factory`); `protocol_hosts.py` documents host protocols for pipeline mixins. API lifespan and the run worker share `nimbusware_orchestrator.runtime_bootstrap.build_runtime_orchestrator`.

**Hardware events:** `POST /v1/platform/hardware/rescan` accepts optional `emit_event` + `run_id` to append `hardware.profile.detected`. Mid-run governor sampling may append rate-limited `resource.pressure.warn` events (projections: pressure headline + pressure-history timeline). Memory index rebuild at run start defers when `sample_pressure` is not `ok` (governor RAM cap). Admin **Hardware** tab reads `GET /v1/platform/analytics/pressure-history` (last-N timeline).

**Deploy:** Production Kubernetes installs use the Helm chart at [`charts/nimbusware`](charts/nimbusware) ([`docs/deploy/helm.md`](docs/deploy/helm.md)); raw manifests under [`docs/deploy/k8s/`](docs/deploy/k8s/README.md) remain a reference path verified by quarterly `k8s_reference_smoke.yml`.

**CI layout (PR):** `.github/workflows/ci.yml` runs **unit** (ruff, `audit_operator_env`, mypy, bandit, pip-audit, pytest @ 75%), **web** (vitest maker + admin, Playwright `tests/e2e/web`), **integration**, and **e2e** jobs in parallel. Local parity: `scripts/ci_check.ps1` / `ci_check.sh` (unit + optional web when Node is present).

**Operator analytics:** `GET /v1/platform/analytics/competitive-summary` and `GET /v1/platform/analytics/bundle-outcomes` on Admin **Metrics**; stitch transplant stats via `GET /v1/platform/analytics/stitch-outcomes` (Run detail **StitchSummaryPanel**). Persona shelf overlap: `GET /v1/personas/overlap-report` (Config → Personas).

**Pipeline typing:** All `_pipeline` mixin modules import `_helpers` symbols without `attr-defined` ignores; `_helpers.py` exports an explicit `__all__` (size-guard allowlisted in `test_package_module_size.py`).

**PEP 561:** Core libraries ship `py.typed` markers (`agent_core`, `nimbusware_store`, `nimbusware_orchestrator`, `nimbusware_config`, `nimbusware_projections`, `nimbusware_executor`, `nimbusware_iam`, `nimbusware_env`, plus UI/API packages).

**CI parity:** `ci_check.*` runs ruff check + **blocking** format, mypy (targets above), bandit (`pyproject.toml`), pip-audit, package coverage floors, pytest @ 75%.

**Size guards:** `test_console_module_size.py` (400 lines), `test_package_module_size.py` (450 lines), `test_module_integrity.py` (anti-gutted facades), `test_pipeline_helpers_exports.py` (orchestrator mixin surface).
