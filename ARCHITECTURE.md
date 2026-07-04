# Nimbusware architecture

## Nomenclature

| Name | Meaning |
|------|---------|
| **Nimbusware** | This repository and product: local-first adversarial agent platform (API, Maker, Admin Console, orchestrator, event store, config, IAM). Use `NIMBUSWARE_*` env vars; Python packages are short names (`api`, `orchestrator`, `env`, …) under `packages/`. |

One-page map of packages, data flow, and auth. Normative Nimbusware agent contract: gitignored `nimbusware-orchestrator-local-plan.md` (repo root, §1–§20.32). Maturity backlog: gitignored `PLAN_GAP.md`. ADR index: [docs/architecture.md](docs/architecture.md).

## Layer diagram

```text
┌─────────────────────────────────────────────────────────────┐
│  UI (web + pywebview desktop)                                │
│  maker_web (/v1/maker/app)  admin_ui   │
│  console (services + display modules for Admin BFF) │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP /v1
┌────────────────────────────▼────────────────────────────────┐
│  api (FastAPI)                                    │
│  UserDep / AdminDep · OpenAPI user/admin tags                │
└─────┬──────────────────┬──────────────────┬─────────────────┘
      │                  │                  │
      ▼                  ▼                  ▼
 orchestrator  projections  iam
 (RunOrchestrator)    (timeline read models)   (Enterprise keys)
      │
      ▼
 store (append-only events)  +  config (YAML→Postgres)
      │
      ▼
 PostgreSQL (or InMemoryEventStore without NIMBUSWARE_DATABASE_URL)
```

## Packages

Full catalog (responsibilities, subpackages, README links): **[packages/README.md](packages/README.md)**.

| Package | Role |
|---------|------|
| `agent_core` | Event models (`models/`), `context_budget`, slice handoff models, `stage_graph`, `slice_plan`, `prompt_tiers`, `critique_stages`, `read/campaign`, `read/critic_matrix` |
| `store` | Event store (Postgres / memory) |
| `orchestrator` | Run pipeline entry (`pipeline.py`, `_pipeline/` mixins) plus domain subpackages: `workflow/`, `slice/`, `fleet/`, `critique/`, `campaign/`, `factory/`, `dev_env/`, `routing/`, `integrator/`, `collab/`, `replay/`, `repo_intel/`, `profiles/`, `scraper/`, `stack/`, `llm/` — see [ADR 028](docs/adr/028-package-directory-depth.md) |
| `memory` | Repo-scoped retrieval index (`store/`, `index/`, `fleet/` subpackages) |
| `extensions` | Personas, bundles, escalation helpers |
| `executor` | Role-gated outbound HTTP |
| `research` | Research briefs, stitch transplant stages, stitch read models and outcome stats |
| `agent_tools` | JIT `agent_loop`, dual `ToolResult` output, tool allowlist, stable prompt file; jail + sandbox + risk caps |
| `config` | Versioned config documents + materializer; canonical **`configs/model-routing.yaml`** (policy, providers, bindings, presets) |
| `projections` | Events → timeline, maker-progress, theater (`run_theater` + **`fields/theater_metadata`**), context budget, `factory_status`, agent-tool prune (+ export, research briefs); gate-family builders share `builders/timeline_history.py` |
| `maker_web` | Alpine Maker web app (tabs, SSE progress, session hub, compaction theater, findings, operator ribbons) at `/v1/maker/app` |
| `admin_ui` | Preact Admin SPA at `/v1/admin/app` (Enterprise fleet at `/fleet`) |
| `mcp` | Stdio MCP IDE bridge (`nimbusware-mcp`; classify, patch / patch-from-selection, interject, chat graph/fork; run status, theater, pending slices, campaign pause/resume; see `docs/ide-bridge.md`) |
| `api` | REST control plane; run-list cursor encoding in `run_list_cursor.py` |
| `client` | Shared HTTP client for Maker + Admin UIs |
| `iam` | Enterprise tenants, API keys, IAM action log for audit export |
| `maker` | Maker server logic — `chat/`, `intent/`, `readiness/`, `workspace/`, `deploy/`, `collab/` subpackages; `services/` + `slice_workflow/` |
| `console` | Admin display helpers + enterprise fleet formatters; workflow explainers use `explainer_core/` (`schema_metrics`, `field_caption`, `env_captions`, `repo_yaml`, `operator_metrics_exports.install_operator_metrics_module`, `workflow_exports.run_id_export_filename_slug`, `table_rows_csv`, `workflow_payload_header`); display field tuples shared with `projections/fields/` where possible; BFF via `admin_ui_bff.py` |
| `env` | Edition gate, OIDC config, desktop launchers, dotenv, **~256-key** settings catalog + `settings_facade` / `settings_resolve` / `env_flags`, admin token guards |
| `hw` | Probe, governor, pressure, catalog fit; local + Enterprise SSH remote probe; `/v1/platform/hardware`, `/v1/platform/hardware/fleet`, `/v1/platform/models/*` |
| `auth` | Local collaborative-chat auth (register/login, session tokens) when `NIMBUSWARE_COLLAB_ENABLED=1` |
| `compute` | Compute mesh node registry, work-unit queue, worker policy (`nimbusware-compute-worker` CLI) |

## v1.2 extensions (Jun 2026)

- **Model Hub & install profiles** — `recommended` / `barebones` installer profiles; Model Hub tab for Ollama + API connection vault ([`docs/model-hub.md`](docs/model-hub.md), [ADR 024](docs/adr/024-install-profiles.md)).
- **Per-role model routing** — `ModelBindingResolver`, user defaults in Postgres, mid-chat swap, enterprise model policy ([ADR 022](docs/adr/022-per-role-model-routing.md), [`docs/audits/llm-call-sites.md`](docs/audits/llm-call-sites.md)).
- **Collaborative chat** — opt-in multi-participant sessions, invites, host transfer MVP ([`docs/collaborative-chat.md`](docs/collaborative-chat.md), [ADR 023](docs/adr/023-collaborative-chat-sessions.md)).
- **Compute mesh** — node register/heartbeat, mesh worker stage execution, session compute opt-in ([`docs/compute-mesh.md`](docs/compute-mesh.md), [ADR 025](docs/adr/025-distributed-compute-mesh.md)).

## Editions

| Edition | Auth |
|---------|------|
| **Individual** (default) | User routes open on loopback only; non-loopback bind requires `X-Nimbusware-Admin-Token` (same as admin routes). Admin routes always require the token. |
| **Enterprise** | All routes need `X-Nimbusware-Api-Key`; scopes `maker_user` / `maker_admin` |

## Data flow

1. **Create** — Maker `POST /v1/runs` (or Admin lifecycle) appends `run.created` via `RunOrchestrator` → `store`.
2. **Pipeline** — Orchestrator mixins append stage events; projections rebuild timelines and maker-progress from the event log.
3. **Read** — Shared row parsers and read-model helpers live in `agent_core.read` (`campaign`, `critic_matrix`) and `agent_core.stage_graph`. HTTP handlers use `projections` / `read_models/`; Admin BFF routes call `console` display formatters.
4. **Maker loop** — Pending slices, research approve/reject, stitch summary, and launch readiness scorecards are read models over the same event log (`maker` + maker web tabs). **Chat sessions** (`nimbusware_chat_session` / `nimbusware_chat_turn`, or in-memory `ChatStore`) persist operator turns and DAG branches; runs started from Chat append to the event store as usual.

## Config authority

When `NIMBUSWARE_CONFIG_FROM_DB=1`, hot paths (orchestrator `_base_cfg`, integrator gate, Admin `bundle_catalog/catalog_local`, `persona_catalog` critique pairings, escalation/self-refinement explainers) read versioned documents from Postgres via `ConfigMaterializer` (`load_bundle_catalog_content`, `load_critique_pairings_doc`, `get_escalation_policy`, `get_model_routing_base`, …). Repo `configs/` YAML is the gitops export/review surface (`export_config_to_repo`), not the runtime source of truth in DB mode.

## Auth (request path)

| Surface | Header / cookie |
|---------|------------------|
| Maker user routes | Open on loopback (Individual); `X-Nimbusware-Api-Key` (`maker_user`) on Enterprise |
| Admin API routes | `X-Nimbusware-Admin-Token` (Individual); `maker_admin` key (Enterprise) |
| Admin SPA SSO | Optional OIDC session cookie for shell only — API calls still need admin token / API key ([docs/deploy/oidc.md](docs/deploy/oidc.md)) |

## Import rules (enforced)

- `extensions` must not import `orchestrator` at module level (`tests/unit/test_import_graph.py`).
- `orchestrator` must not import `api` (Lane R-C — use `projections`).
- `projections` must not import `orchestrator` at module level (`tests/unit/test_import_graph.py`).
- Legacy package-name shims (`nimbusware_*` → short names) removed; import `api`, `orchestrator`, `env`, etc. directly.

## Architecture decision records

See [docs/architecture.md](docs/architecture.md) for ADR links (event store, edition gate, projections, logging, correlation IDs).

## Refactor playbook

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) for setup, CI, and production secrets. Day-to-day workflow:

| Step | Command / guard |
|------|-----------------|
| Local CI | `./scripts/ci/ci_check.ps1` or `scripts/ci/ci_check.sh` |
| After display package splits | `poetry run python scripts/ci/explicit_star_imports.py` |
| After package `__init__` export changes | `poetry run python scripts/ci/sync_display_facade.py` |
| Facade contract | `tests/unit/test_display_facade_exports.py` |

**Do not** run repo-wide `ruff check --fix` — it strips explicit re-export imports.

**Coverage:** CI enforces `--cov-fail-under=75` on the default unit subset. Per-package floors (≥85%): `agent_core`, `store`, `executor`, `config`, `projections` via `scripts/ci/coverage_package_floors.py`. Web static assets (`maker_web`, `admin_ui`) and desktop launcher modules are omitted from the denominator (`pyproject.toml`).

**Typing:** Global mypy `strict = true`. CI checks paths from `scripts/ci/mypy_ci_targets.py`:

| Tranche | Packages / paths |
|---------|------------------|
| B | `projections`, `client`, `agent_tools` |
| C | `agent_core`, `store`, `config`, `executor`, `extensions`, `memory`, `iam`, `env` |
| D | `api/read_models`, `facade`, `deps`, `routes/enterprise`, `routes/personas_helpers` |
| E | Orchestrator islands: orchestrator root modules plus full `_pipeline/*` (including `dev_factory`, `compose`, `protocol_hosts`, `pipeline_scraper`); probation/fast-slice workflow metadata on `run.created` (see `scripts/ci/mypy_ci_targets.py` `_TRANCHE_E`) |
| F | Orchestrator root (`autopilot_profiles`, `micro_slice_*`, `workflow_universal_critique`); API `routes/bundles*`, `routes/chat*` (see `_TRANCHE_F`; console covered by UI tranche) |
| API pilot | `routes/ollama`, `schemas/ollama`, `errors` |
| UI | Full `console` and `maker` under narrowed ignore list; `services/*` strict |

All `_pipeline` modules are strict-checked mypy islands (including `dev_factory`); `protocol_hosts.py` documents host protocols for pipeline mixins. API lifespan and the run worker share `orchestrator.runtime_bootstrap.build_runtime_orchestrator`.

**Hardware events:** `POST /v1/platform/hardware/rescan` accepts optional `emit_event` + `run_id` to append `hardware.profile.detected`. Mid-run governor sampling may append rate-limited `resource.pressure.warn` events (projections: pressure headline + pressure-history timeline). Memory index rebuild at run start defers when `sample_pressure` is not `ok` (governor RAM cap). Admin **Hardware** tab reads `GET /v1/platform/analytics/pressure-history` (last-N timeline).

**Deploy:** Production Kubernetes installs use the Helm chart at [`charts/nimbusware`](charts/nimbusware) ([`docs/deploy/helm.md`](docs/deploy/helm.md)); raw manifests under [`docs/deploy/k8s/`](docs/deploy/k8s/README.md) include optional ingress, NetworkPolicy, HPA, PDB, and a suspended event-store purge CronJob sketch. Enterprise integrator gate: [`docs/deploy/enterprise-integrator-runbook.md`](docs/deploy/enterprise-integrator-runbook.md). Multi-host Redis fleet secrets: [`docs/deploy/production-fleet-redis-secrets.md`](docs/deploy/production-fleet-redis-secrets.md).

**CI layout (PR):** `.github/workflows/ci.yml` runs **unit** (ruff, `audit_operator_env`, openapi TS gate, publish VS Code gate, mypy, bandit, pip-audit, pytest @ 75%, framework-pack + SLO gates), **web** (full OpenAPI schema regen, vitest maker + admin, Playwright `tests/e2e/web`), **integration**, and **e2e** jobs in parallel. Local parity: `scripts/ci/ci_check.ps1` / `ci_check.sh` (unit + optional web when Node is present).

**Operator analytics:** `GET /v1/platform/analytics/competitive-summary` and `GET /v1/platform/analytics/bundle-outcomes` on Admin **Metrics**; stitch stats via `GET /v1/platform/analytics/stitch-outcomes`. Persona shelf overlap: `GET /v1/personas/overlap-report`.

**Pipeline typing:** All `_pipeline` mixin modules import `_helpers` symbols without `attr-defined` ignores; `_helpers.py` re-exports from `_helpers_std.py`, `_helpers_bundle_*`, and `_helpers_runtime.py` with an explicit `__all__`.

**PEP 561:** Core libraries ship `py.typed` markers (`agent_core`, `store`, `orchestrator`, `config`, `projections`, `executor`, `iam`, `env`, plus UI/API packages).

**CI parity:** `ci_check.*` runs ruff check + **blocking** format, openapi TS gate (full schema when Node present; Admin `openapi.json` / `schema.d.ts` are **generated** at build via `npm run codegen:openapi` and gitignored), publish VS Code gate, mypy (targets above), bandit (`pyproject.toml`), pip-audit, framework-pack gate (keyboard/mouse fidelity), package coverage floors, pytest @ 75% (**~4256** collected / **~3355+** in the default unit job, ≥75% line coverage; packages LOC baseline **102,713** max via `scripts/ci/loc_baseline.json`; unified module size guard **≤1000 lines** per `packages/**/*.py` module via `test_package_module_size.py`; optional fast bundle via `scripts/ci/fast_gates.py`; see `tests/README.md`). Enterprise fleet tenant policies live in `fleet_policies.py` with YAML I/O via `fleet_policy_loader.py` and enforcement in `fleet_policy_guards.py`. Workflow block parsers for micro-slice, theater, dev-env, fast-slice, escalation, and integration-adapter-writer live in `workflow_blocks_simple.py`. `load_create_run_workflow_blocks` uses `workflow_registry.parse_workflow_block`; campaign requirement helpers live in `runs/create.py`; deploy models and policy helpers colocate in `platform_deploy.py`; collab discipline/settings routes inline in `platform.py`; intent classifier keyword tables in `intent_classifier_rules.py`; chat scope discovery, session-start, and compute routes colocate in `chat_session.py`; host-transfer and chat library ACL/folder routes colocate in `chat_collab.py`; chat participants + invite/join routes colocate in `chat_participants.py`; seven workflow explainers use YAML metric specs under `configs/explainers/` with caption parts resolved from `explainer_caption_parts` by slug. Optional workflow profiles should `extends: default` instead of copying the full default header block. Enterprise model policy is the `model_policy` section of `configs/model-routing.yaml` (standalone `configs/model_policy.yaml` is optional override on save).

**Size guards:** `test_package_module_size.py` (1000 lines, all `packages/**/*.py`), `test_module_integrity.py` (anti-gutted facades), `test_pipeline_helpers_exports.py` (orchestrator mixin surface), `scripts/ci/import_boundary_check.py` (orchestrator must not import `api` at module level), `scripts/ci/stage_registry_gate.py` (pipeline stage registry completeness).

## Context efficiency (Jul 2026)

Progressive compaction, cache-aware prompts, and token telemetry live under `agent_core/` and `agent_tools/agent_loop.py`:

| Level | Trigger | Module |
|-------|---------|--------|
| L1 offload | Tool result > `NIMBUSWARE_TOOL_OFFLOAD_CHARS` | `agent_core/tool_output_offload.py` |
| L0 microcompact | JIT tokens > threshold | `agent_tools/agent_loop.py` |
| L3 campaign compact | Handoff + budget | `orchestrator/context_compaction.py` |
| L4 full compact | `NIMBUSWARE_AGENT_COMPACT=full` | `agent_core/agent_full_compact.py` |

Cache tiers: `agent_core/prompt_tiers.py` (`assemble_prompt_with_cache_metadata`); provider headers: `orchestrator/llm/prompt_cache.py`. Memory index-first injection: `memory/index/index_table.py` + `NIMBUSWARE_MEMORY_INDEX_FIRST`. Read outline mode: `agent_core/read_outline.py`. Stage plugin contract: `orchestrator/_pipeline/stage_dispatch.py` (`PIPELINE_STAGES`).

**Maker web modules:** Chat (`chat.js` + `chat_session_lifecycle.js`, `chat_shell_html.js`, `chat_run_card_ui.js`, `chat_collab_wiring.js`, `chat_*_ui.js`, solo hat + coach in `chat_solo_hat_ui.js`), Model Hub (`models.js` + `models_local_ui.js`, `models_ollama_ui.js`, `models_*_ui.js`), Review (`review.js` + `review_git_ui.js` incl. deploy audit, `review_*_ui.js`), Home (`home.js` + `home_readiness_ui.js`), Settings (`settings.js` + `settings_shell_html.js`, `settings_*_ui.js`), Progress (`render-chips.js`, `progress_status_chips.js`, `operator-ribbons.js`, `progress_ribbon_refresh.js`). Collab invite modal: `chat_invite_modal_ui.js`. **API platform routes:** `platform.py` composes `platform_hardware.py`, `platform_user_profiles.py`, `platform_model_routing.py`. **Theater projections:** `run_theater_handlers.py` delegates to `run_theater_stage_handlers.py`.
