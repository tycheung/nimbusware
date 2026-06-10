# Nimbusware

Nimbusware is a **local-first** platform for operating adversarial agentic software workflows. It combines a **FastAPI control plane**, **Maker** and **Admin** web apps (Alpine + Preact at `/v1/maker/app/` and `/v1/admin/app/`), optional **desktop shells** (pywebview), and an event-sourced **agent runtime** (multi-role pipeline, unanimous gates, verifiers, optional Ollama-backed LLM stages via `nimbusware_*` packages).

**Default install:** Maker only. The Admin Console is optional and gated behind an admin token.

**Version:** `0.5.0` · **Python:** `>=3.10` (3.11+ recommended) · **Default workflow profile:** `nimbusware_production`

## Product editions

| Edition | Install | Scope |
|---------|---------|--------|
| **Individual** (default) | `python scripts/install_nimbusware.py` | Single operator, repo-scoped memory, no IAM |
| **Enterprise** | `python scripts/install_nimbusware.py --edition enterprise` | Multi-tenant IAM, fleet memory, config NOTIFY, Redis workers, fleet SLI, enterprise console panels |

Set `NIMBUSWARE_EDITION=individual|enterprise` in `.env`. Enterprise-only routes return **404** on Individual. Check gates: `GET /v1/platform/edition`.

**Enterprise capabilities** (when edition is `enterprise`):

- **IAM** — API keys, tenants, row-level isolation on events/config/memory (`X-Nimbusware-Api-Key`)
- **Fleet memory** — org-scoped index, canonical store sync (`nimbusware-memory-sync`), search API
- **Config NOTIFY** — Postgres `LISTEN/NOTIFY` + `config.document.updated` cache invalidation
- **Object-store primary** — S3-compatible scraper artifact backend (optional local mirror)
- **Redis fleet worker** — shared verify queue, health/back-pressure metrics
- **Fleet Ollama SLI** — sustained health p95 export + preflight aggregate API
- **Enterprise fleet (Admin)** — **Fleet** tab at `/v1/admin/app/fleet` (tenant switcher, fleet memory, Ollama SLI aggregate, worker health, hardware tiers, cross-tenant gate comparison; requires `X-Nimbusware-Api-Key` in Admin sign-in)

## Architecture

| Layer | Packages / entry | Role |
|-------|------------------|------|
| **Nimbusware API** | `nimbusware_api` | `/v1` REST, OpenAPI, Problem+JSON errors |
| **Maker app** | `nimbusware_maker` + `nimbusware_maker_web` | **User console** — web UI at `/v1/maker/app/` |
| **Admin Console** | `nimbusware_console` + `nimbusware_admin_ui` | **Admin/dev console** — web UI at `/v1/admin/app/` (Enterprise **Fleet** at `/v1/admin/app/fleet`) |
| **Agent tools** | `nimbusware_agent_tools` | Allowlisted tools; filesystem jail; sandbox (`none`/`stub`/`docker`/`kubernetes`/`e2b`); per-slice risk caps |
| **Nimbusware orchestrator** | `nimbusware_orchestrator`, `agent_core` | Run pipeline, critics, gates, slice chain, preflight |
| **Event store** | `nimbusware_store` | Append-only Postgres (or in-memory without DB URL) |
| **Config store** | `nimbusware_config` | Versioned Postgres documents + materializer (T1/T2) |
| **Memory** | `nimbusware_memory` | Repo-scoped retrieval index (Individual); fleet scope (Enterprise) |
| **IAM** | `nimbusware_iam` | Enterprise tenancy and API keys |
| **Extensions** | `nimbusware_extensions` | Personas, bundles, escalation, integrator helpers |
| **Research / stitch** | `nimbusware_research` | Research briefs, stitch stages, outcome analytics |
| **Projections** | `nimbusware_projections` | Pure event → timeline read models (no API import from orchestrator) |
| **UI HTTP client** | `nimbusware_client` | Shared Maker + Admin `/v1` client (Problem+JSON, auth headers) |
| **Desktop / env** | `nimbusware_env` | Edition gate, `env_flags`, admin token guards, desktop launchers |

Optional: **Ollama** for LLM stages (`NIMBUSWARE_USE_LLM=1`), **Redis** for multi-worker dispatch, **FAISS** for bundle/memory vector search (`poetry install --with faiss`). **Pyright LSP** for slice symbol sketch ships with default `poetry install` (dev dependency); installer sets `NIMBUSWARE_SLICE_LSP_ENABLED=1` in `.env`.

Environment toggles use the **`NIMBUSWARE_*`** prefix and are centralized in [`packages/nimbusware_env/env_flags.py`](packages/nimbusware_env/env_flags.py). See [`.env.example`](.env.example).

Developer docs: [ARCHITECTURE.md](ARCHITECTURE.md) (canonical package map), [docs/README.md](docs/README.md) (doc index), [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [tests/README.md](tests/README.md). Operators: [bundle catalog promotion](docs/operator-bundle-catalog-promotion.md), [enterprise buyer checklist](docs/enterprise-buyer.md), [security CI gates](docs/security-quality-gates.md). Web UIs call `/v1` via `fetch` or `nimbusware_client`; Python display helpers use `packages/*/services/` (no direct HTTP in `*_display.py`).

## Agent runtime

The orchestrator and related packages provide:

- **Run lifecycle** — `run.created` → plan → implement/verify paths with frozen `policy_snapshot` from materialized config
- **Adversarial critics** — domain-bound critique stages (security, performance, network/resilience, refactor on production profile)
- **Unanimous gates** — stage progression blocked until critics/verifiers pass (with escalation anti-deadlock)
- **Parallel writers** — frontend/backend writers with role taxonomy and failure routing
- **Bundle integrator** — catalog search, FAISS ranking, compatibility scoring, integrator gate (live adapter probe on gate metadata); optional GitHub Checks or GitLab commit status bridge ([docs/deploy/external-ci-bridge.md](docs/deploy/external-ci-bridge.md))
- **Personas** — business + development shelves, persona assignment, agent evaluator + persona coverage critic; **probation automation** (reliability auto-shelve, promote notice; `GET /v1/personas/{shelf}/{persona_id}/probation-reliability`)
- **Self-refinement** — gated/ungated loops with Phase D markers and optional LLM critique
- **Fast slice** (`fast_slice: true` or `NIMBUSWARE_FAST_SLICE`) — skip optional universal critic matrix and slice LLM critique when max finding severity is below HIGH
- **Micro-slice workflow** (`workflow_profile=micro_slice`) — bounded files/LOC per slice (Maker preset `NIMBUSWARE_SLICE_BUDGET_PRESET`: tiny / standard / careful), per-slice verify → critique → test → optional `slice.e2e` browser verify → gate, diff-aware replan, context packets, optional memory excerpt injection; maker runs auto-advance the slice chain by default (`NIMBUSWARE_SLICE_AUTO_ADVANCE` unset or `1`; set `0` to pause for plan/slice approval)
- **Autonomous campaign** (`workflow_profile=campaign_micro_slice`) — prompt → delivery backlog → one slice per worker tick until tiered completion (slice terminal + optional project tests / feature coverage / deep-eval cadence). Start via `POST /v1/campaigns` or Maker **Chat** (campaign work type). When `NIMBUSWARE_USE_LLM=1` and `NIMBUSWARE_BACKLOG_GENERATOR_MODEL` are set, campaigns use the LLM backlog generator automatically (stub otherwise); Maker **Home** readiness reports `campaign_backlog` status. Maker **Progress** exposes pause/resume/cancel; Admin run detail shows campaign progress, backlog tree, and maintenance events. Requires run worker with `NIMBUSWARE_RUN_DISPATCH=memory` (or redis). Env: `NIMBUSWARE_BACKLOG_MAX_SLICES`, compaction/context-budget from Pi transplant.
- **Slice browser verify (`slice.e2e`)** — **on by default** (`slice.e2e.enabled: true` in [`configs/workflows/micro_slice.yaml`](configs/workflows/micro_slice.yaml)). Use [`configs/workflows/micro_slice_web.yaml`](configs/workflows/micro_slice_web.yaml) for the explicit **web-first** profile (HTML globs). Install Playwright (`poetry run playwright install`) or set `NIMBUSWARE_SLICE_E2E_COMMAND` to a custom shell command. If the runner or `tests/e2e` is missing, the stage **SKIP**s and the slice gate still passes. Default PR **unit** CI runs the `micro_slice_web` apply journey gate when `NIMBUSWARE_SLICE_E2E_COMMAND` is set (see [`scripts/ci_check.ps1`](scripts/ci_check.ps1)); PR **web** job runs **34** Playwright tests across **23** spec files in [`tests/e2e/web`](tests/e2e/web) (including Chat patch/override, operator ribbons, mobile theater parity).
- **Factory scaffold (v2 preview)** — PUT preview runtime (`put_runtime.py`), factory tiers T0–T3 (`factory_completion.py`, [`configs/factory/factory_tier_policy.yaml`](configs/factory/factory_tier_policy.yaml)), interaction surface map with optional runtime crawl (`interaction_surface_map.py`), PUT E2E flow runner (`put_e2e_runner.py`, [`configs/factory/flows/`](configs/factory/flows/) incl. `crm`, `static_site`, `contacts_api`, `todo_api`); PUT E2E failure evidence zip (`put_e2e_evidence.py`); automatic factory cadence on maintenance passes (`factory_cadence.py`, profiles [`campaign_factory_zero_touch.yaml`](configs/workflows/campaign_factory_zero_touch.yaml) and [`campaign_factory_t3.yaml`](configs/workflows/campaign_factory_t3.yaml)); weekly job [`scripts/run_factory_weekly_ci.py`](scripts/run_factory_weekly_ci.py) with multi-entry [`golden_factory_replay_manifest.json`](tests/fixtures/factory/golden_factory_replay_manifest.json) in [`.github/workflows/slow_tests.yml`](.github/workflows/slow_tests.yml) (`factory-weekly`); opt-in PR PUT E2E gate via `put-e2e` label ([`scripts/run_put_e2e_ci_gate.py`](scripts/run_put_e2e_ci_gate.py)); fleet remote Playwright pool via `NIMBUSWARE_FLEET_PLAYWRIGHT_WS_ENDPOINT` (`fleet_playwright.py`); factory evidence `GET /v1/runs/{id}/factory-evidence` and zip `.../factory-evidence/export` (`factory_evidence.py`).
- **Persistent launch dev environment (v2.1)** — workspace-scoped session supervisor keeps preview servers running across slices (`dev_env_supervisor.py`); framework adapters with uvicorn `--reload` and npm dev (`dev_env_adapters.py`); incremental HTTP regression without restart (`dev_env_regression.py`); UI controller with mouse/keyboard DSL (`browser_controller.py`, `ui_flow_dsl.py`); API `GET/POST /v1/runs/{id}/dev-env/*`; ADR [009](docs/adr/009-persistent-dev-environment.md) and [010](docs/adr/010-ui-controller.md). Env: `NIMBUSWARE_DEV_ENV_ENABLED`, `NIMBUSWARE_DEV_ENV_BASE_URL`, `NIMBUSWARE_UI_CONTROLLER_ENABLED`.
- **Variable PUT launch testing (v2.4)** — resolve HTTP + UI flows per prompt/stack (`launch_flow_resolver.py`); catalog UI flows in [`configs/factory/ui_flows/`](configs/factory/ui_flows/) (e.g. `todo_api_ui`); Playwright locators via role/testid/label/text; full-stack sessions expose `api_base_url` + `frontend_base_url`; launch-test writer/critic stages on [`micro_slice_fullstack`](configs/workflows/micro_slice_fullstack.yaml) with ISM synthesis, optional LLM writer (`launch_test_llm.py`), and critique replan loop (`launch_test_stage.py`); nine JS framework packs in [`configs/launch_test/frameworks/`](configs/launch_test/frameworks/) (react/vue/angular/svelte/static/spa + next/nuxt/remix) with `writer_instructions` in `build_launch_test_writer_prompt()`; golden fixtures [`tests/fixtures/repos/tiny_todo_fullstack/`](tests/fixtures/repos/tiny_todo_fullstack/) and [`tests/fixtures/repos/tiny_spa_unknown/`](tests/fixtures/repos/tiny_spa_unknown/); journeys include fullstack launch, unknown-SPA synthesis, and write-replan UI+keyboard (`tests/e2e/journeys/`). Maker **Progress** dev-env ribbon and **Launch scorecard** show `put_ui_flow_id`, `slice_e2e_passed`, and UI failure step/locator. Factory **T2b** cadence runs UI regression after PUT HTTP E2E. PR **unit** CI runs [`scripts/run_framework_pack_ci_gate.py`](scripts/run_framework_pack_ci_gate.py); weekly **fullstack-weekly-soak** via [`scripts/run_fullstack_weekly_soak.py`](scripts/run_fullstack_weekly_soak.py). Env: `NIMBUSWARE_LAUNCH_TEST_ENABLED`, `NIMBUSWARE_LAUNCH_TEST_WRITER_MODEL` (with `NIMBUSWARE_USE_LLM=1`).
- **Human-fidelity + diagnose/learn** — lang/heading/perf-budget smoke, optional axe-core rule packs (`NIMBUSWARE_AXE_ENABLED=1`), keyboard-nav, and optional negative-login paths (`human_fidelity.py`); failure learnings under `docs/learnings/` with stack fingerprint (`diagnose_learn.py`); learnings API + Maker panel; ADR [011](docs/adr/011-human-fidelity-e2e.md), [012](docs/adr/012-diagnose-fix-learn.md).
- **Operator interjection + autopilot** — Next/Last interjection queue (`interjection_queue.py`, `GET/POST /v1/runs/{id}/interjection-queue`); message prefixes `[patch]` (head patch slice), `[steer]` (JIT volatile prompt), `[skip]` (defer backlog slice), plus existing `[build]`; autopilot slider presets 0–10, per-run override (`autopilot_profiles.py`, `GET/PUT /v1/runs/{id}/autopilot`, [`configs/autopilot/presets.yaml`](configs/autopilot/presets.yaml) — level **8 “Nimble”** is the default posture for patch runs (`stop_on_slice_test_fail`, `stop_at_terminal_review`)); saved operator profiles (`user_autopilot_profiles.py`, `GET/PUT /v1/platform/autopilot/user-profiles/{id}`, optional `autopilot_profile_id` on `POST /v1/runs`, `POST /v1/campaigns`, and chat start); workspace learnings panel (`learnings_catalog.py`, `GET /v1/runs/{id}/learnings`); launch eval merges dev-env HTTP/UI regression from run events; slice-cycle wiring (`slice_cycle_integration.py`) drains interjection, runs dev-env pre-gate regression, resolution council, diagnose-learn, and improvement council ticks; ADR [013](docs/adr/013-operator-interjection.md)–[015](docs/adr/015-custom-autopilot-profiles.md), [020](docs/adr/020-unified-chat-work-type-routing.md).
- **Patch lane** (`workflow_profile=patch`, [`configs/workflows/patch.yaml`](configs/workflows/patch.yaml)) — hotfix profile: one bounded slice (max 2 files / 60 LOC), minimal stage graph (plan → implement → verify → test → gate, no E2E), `fast_slice`, auto-apply caps (`max_loc` 40, `max_files` 1, tests must pass), targeted test from `patch_context` (`target_paths`, `failing_test`, `stack_trace`); `maker_approval` off; escalation to micro-slice offered in chat when patch gate fails; frozen `work_type` / `work_type_source` on `run.created` metadata.
- **Code intelligence + continuous improvement** — in-repo code graph, orphan/similarity/cohesion indexes (`code_graph.py`, `orphan_index.py`, `similarity_index.py`, `cohesion_graph.py`); `inventory_health_score` in `repo_inventory.py` weights improvement-council votes (`improvement_council.py`); allowlisted graph tools (`repo_graph_tools.py`); repo explorer and variant arena with workspace promotion (`repo_explorer.py`, `variant_arena.py`); debate-first resolution council with loc accord before remediable gate blocks (`resolution_council.py`); council deliberation lines in theater; ADR [016](docs/adr/016-repo-exploration-variants.md)–[019](docs/adr/019-debate-first-resolution.md).
- **Parallel optional critics** — when `hardware_tier=strong`, set `NIMBUSWARE_ALLOW_PARALLEL_CRITICS=1` (or `parallel_critics.enabled: true` in the workflow profile) to run security/performance/network resilience critiques concurrently during verify instead of sequential short-circuit.
- **Mid-run pressure warnings** — rate-limited `resource.pressure.warn` events when the hardware governor throttles RAM mid-run; Admin **Hardware** timeline and competitive-summary projections surface the tail
- **Slice implement agent** — `NIMBUSWARE_SLICE_IMPLEMENT=agent` uses a multi-turn JIT tool loop (`agent_loop.py`) with `read`, `edit`, `write`, `grep`, `shell`, and optional `browser_act` (Playwright UI steps against the active dev-env URL); no upfront file preload when `NIMBUSWARE_AGENT_JIT_LOOP=1` (default)
- **Cross-slice handoffs** — deterministic `slice.handoff` summaries feed planner and agent volatile prompts (not full unified diffs)
- **Campaign compaction** — `campaign.context.compacted` events summarize older handoffs in long runs (`NIMBUSWARE_CAMPAIGN_COMPACT_ENABLED`)
- **Slice symbol sketch** — Pyright LSP `documentSymbol` by default (`NIMBUSWARE_SLICE_LSP_ENABLED=1` after install; bundled via `poetry install`; override with `NIMBUSWARE_SLICE_LSP_COMMAND`); AST fallback when LSP is off or unavailable
- **Preflight** — Ollama/model health at run start; CLI and fleet history APIs
- **Scraper stage** — role-gated HTTP fetch with on-disk or object-store artifacts and retention/prune tooling
- **Retrieval memory** — index findings/gate failures; replay harness; role telemetry and routing suggestions (read-only CLI)

Configs live under [`configs/`](configs/) (workflows, personas, roles, `model-routing.yaml` including `ollama_user_policy`, bundles, `critic_packs/`, `skills/`). With Postgres, operator edits persist to `nimbusware_config_document` and materialize at API startup (optional git export via `nimbusware-config`). Bundle catalog authority is YAML under the repo root unless `NIMBUSWARE_DATABASE_URL` is set, in which case `policy/bundle-catalog` in Postgres is authoritative (`GET /v1/bundles/catalog/source`).

## Context efficiency (Pi-inspired)

Token-aware caps keep LLM prompts bounded without deleting raw audit events. See [ADR 006](docs/adr/006-prompt-tiers.md) and [ADR 007](docs/adr/007-context-compaction.md).

| Flag | Default | Purpose |
|------|---------|---------|
| `NIMBUSWARE_LLM_HISTORY_MAX_CHARS` | 2000 | Secondary LLM stages and tool message history |
| `NIMBUSWARE_READ_MAX_CHARS` | 16000 | Agent `read` tool output |
| `NIMBUSWARE_SHELL_OUTPUT_MAX_CHARS` | 4000 | Agent `shell` output |
| `NIMBUSWARE_AGENT_JIT_LOOP` | 1 | Multi-turn agent loop vs single-shot plan |
| `NIMBUSWARE_AGENT_TOOLS` | read,write,edit,grep,shell | Agent tool allowlist (optional `find`, `ls`, `browser_act`, `write_ui_flow`, `run_ui_regression`) |
| `NIMBUSWARE_THEATER_LLM_SUMMARY` | off | Append rules-based theater digest when `1` or run metadata `theater.llm_summary` |
| `NIMBUSWARE_AXE_ENABLED` | off | Run axe-core rule packs in human-fidelity suite |
| `NIMBUSWARE_PROJECTION_PRUNE_AGENT_TOOLS` | 1 | Prune stale agent tool lines in theater/timeline |
| `NIMBUSWARE_AGENT_COMPACT` | 1 | `POST /v1/runs/{id}/compact` and MCP `nimbusware_compact_run` |
| `NIMBUSWARE_BACKLOG_MAX_SLICES` | 500 | Max slices in campaign delivery backlog |
| `NIMBUSWARE_BACKLOG_GENERATOR_MODEL` | (empty) | Ollama model for LLM backlog; empty uses stub |
| `NIMBUSWARE_RUN_DISPATCH` | (off) | `memory` or `redis` to enable campaign tick worker |
| `NIMBUSWARE_EMBED_DISPATCH_WORKER` | 0 | Start in-process dispatch worker thread during API lifespan (memory queue; stack E2E) |
| `NIMBUSWARE_ALLOW_PARALLEL_CRITICS` | 0 | When `hardware_tier=strong`, run optional security/performance/network critiques concurrently during verify |
| `NIMBUSWARE_INTEGRATOR_PROBE_MAX_ATTEMPTS` | 3 | Max HTTP health probe attempts for api_bridge integrator sync |
| `NIMBUSWARE_INTEGRATOR_PROBE_RETRY_DELAY` | 0.25 | Base seconds between integrator probe retries (exponential backoff) |
| `NIMBUSWARE_HANDOFF_MAX_CHARS` | 4000 | Cross-slice handoff block |
| `NIMBUSWARE_HANDOFF_LLM_SUMMARY` | 0 | Optional LLM handoff refinement |
| `NIMBUSWARE_CAMPAIGN_COMPACT_ENABLED` | 1 | Summarize older handoffs in long campaigns |
| `NIMBUSWARE_CAMPAIGN_KEEP_RECENT_TOKENS` | (from HW) | Verbatim recent handoff window |
| `NIMBUSWARE_CAMPAIGN_RESERVE_TOKENS` | 8000 | Output reservation subtracted from keep window |
| `NIMBUSWARE_CONTEXT_ARTIFACT_FAISS_REBUILD` | 0 | Rebuild memory FAISS after context-artifact bridge-memory |
| `NIMBUSWARE_FLEET_PLAYWRIGHT_WS_ENDPOINT` | (empty) | Optional remote Playwright WS for fleet PUT E2E (Enterprise) |
| `NIMBUSWARE_MAKER_VAPID_PUBLIC_KEY` | (empty) | Enables Maker Web Push subscription API when set |
| `NIMBUSWARE_MAKER_VAPID_PRIVATE_KEY` | (empty) | VAPID private key for server-side campaign push notifications |
| `NIMBUSWARE_MAKER_VAPID_SUBJECT` | (empty) | VAPID subject (`mailto:…`) for push send |
| `NIMBUSWARE_PUT_SANDBOX` | (empty) | Set to `docker` to run PUT preview inside Docker |
| `NIMBUSWARE_DEV_ENV_ENABLED` | 0 | Enable persistent dev environment on factory profiles |
| `NIMBUSWARE_DEV_ENV_BASE_URL` | (empty) | Attach to external dev server instead of spawning |
| `NIMBUSWARE_DEV_ENV_PORT_BASE` | 19800 | Base port for dev env session allocation |
| `NIMBUSWARE_UI_CONTROLLER_ENABLED` | 0 | Enable UI controller regression stages |
| `NIMBUSWARE_LAUNCH_TEST_ENABLED` | 0 | Enable launch-test writer/critic stages on full-stack profiles |
| `NIMBUSWARE_FACTORY_EXPLORATORY_CRAWL` | (empty) | Set to `1` for bounded Playwright ISM crawl on factory T3 |
| `NIMBUSWARE_FACTORY_EVIDENCE_OBJECT_STORE_URL` | (empty) | S3-compatible URL to mirror factory evidence zip exports |
| `NIMBUSWARE_FACTORY_EVIDENCE_OBJECT_STORE_BUCKET` | (empty) | Bucket name for factory evidence object store |

Shared helpers: `packages/agent_core/context_budget.py`. Context budget API: `GET /v1/runs/{id}/context_budget` (advisory chip on Maker Progress; includes `last_compaction`). Compaction revert: `POST /v1/runs/{id}/compactions/{compaction_id}/revert`. Replay-from-checkpoint: `POST /v1/runs/{id}/replay-from` with `operator_ack` and optional `compact_enabled` / `ignore_compaction_ids` (re-enqueues `campaign_tick` on campaign runs). Context artifacts: `GET/POST /v1/projects/{id}/context-artifacts`; save latest compaction: `POST /v1/runs/{id}/context-artifacts/from-compaction`; insert into run: `POST /v1/runs/{id}/context-artifacts/{artifact_id}/insert`; bridge to memory sidecar: `POST .../context-artifacts/{artifact_id}/bridge-memory` (optional env-gated FAISS rebuild via `NIMBUSWARE_CONTEXT_ARTIFACT_FAISS_REBUILD=1`). Memory library insert: `POST /v1/runs/{id}/memory-chunks/{chunk_id}/insert`. File-cache persistence: [docs/adr/008-context-artifacts-file-cache.md](docs/adr/008-context-artifacts-file-cache.md). Stable agent rules: `configs/prompts/agent_implement_stable.txt`. Skills progressive disclosure: `configs/skills/` + `nimbusware_config.skills_index`.

## Benchmarks

Optional **SWE-bench-style** regression harness for the `micro_slice` workflow profile:

- Script: [`scripts/swe_bench_harness.py`](scripts/swe_bench_harness.py)
  - `--dry-run --json` — validate manifest + fixture layout
  - `--run --json` — score in-memory `micro_slice` pass against the fixture workspace (`slices_total`, `gates_passed`, `gates_failed`, `pass_rate`, `duration_sec`, `run_id`)
- Fixture: [`tests/fixtures/swe_bench/`](tests/fixtures/swe_bench/) (`min_pass_rate` in `manifest.json`)
- Published metrics: gitignored [`benchmarks/`](benchmarks/) — set `NIMBUSWARE_SWE_BENCH_WRITE_JSON=1` to write `benchmarks/latest_swe_bench.json`
- CI: weekly [`.github/workflows/swe_bench.yml`](.github/workflows/swe_bench.yml) dry-run + **required** scored `--run` (`min_pass_rate: 1.0`); artifact `latest_swe_bench.json` (copy into `benchmarks/` for Admin Metrics)
- Env: `NIMBUSWARE_SWE_BENCH_ENABLED`, `NIMBUSWARE_SWE_BENCH_MANIFEST`, `NIMBUSWARE_SWE_BENCH_WRITE_JSON`

Example scored output:

```json
{
  "ok": true,
  "mode": "run",
  "pass_rate": 1.0,
  "slices_total": 1,
  "gates_passed": 1,
  "gates_failed": 0,
  "duration_sec": 12.5,
  "run_id": "..."
}
```

## Repository layout

```
packages/
  agent_core/           Event models, context_budget, slice handoff models
  nimbusware_orchestrator/  Pipeline, critics, slice, handoff, compaction, prompt_tiers
  nimbusware_store/         Postgres + in-memory event store
  nimbusware_memory/        Memory chunks, FAISS, fleet sync
  nimbusware_executor/      Role-gated outbound HTTP
  nimbusware_extensions/    Personas, bundles, catalog
  nimbusware_api/       FastAPI app
  nimbusware_maker/     Maker services, slice workflow, onboarding helpers
  nimbusware_maker_web/ Maker web UI static assets (Alpine)
  nimbusware_admin_ui/  Admin Preact SPA (built to dist/)
  nimbusware_hw/        Hardware probe, resource governor, model fit ranking
  nimbusware_console/   Admin display helpers + services (ops/dev)
  nimbusware_agent_tools/   Allowlisted agent tool runtime for slice implement
  nimbusware_config/    Config store + NOTIFY
  nimbusware_iam/       Enterprise IAM
  nimbusware_client/    Shared HTTP client for Maker + Admin UIs
  nimbusware_projections/  Timeline read-model helpers
  nimbusware_env/       Edition gate, env_flags, desktop runners
configs/                Workflow YAML, personas, bundles (seed / gitops review)
scripts/                Install, FAISS build, workers, e2e smoke, runbooks
tests/                  Pytest suite (unit/api/console/orchestrator/integration/e2e)
```

Generated/local paths are **gitignored** (`.cache/`, `.nimbusware/`, `docs/learnings/`, `configs/memory/`, `configs/bundles/index/`, `.env`).

## Quick start

### 1. Dependencies

```bash
poetry install
# Includes dev tools and Pyright langserver (slice LSP). Optional extras:
poetry install --with faiss    # bundle + memory FAISS indexes
poetry install --with redis    # Enterprise Redis dispatch (included for --edition enterprise)
```

### 2. Bootstrap (recommended)

```bash
python scripts/install_nimbusware.py
# Enterprise:
python scripts/install_nimbusware.py --edition enterprise
# Installer also sets NIMBUSWARE_SLICE_LSP_ENABLED=1 in .env (default; use --no-enable-slice-lsp to skip)
```

The installer can set up Poetry deps, Postgres (Docker or native), apply [`packages/nimbusware_store/schema/postgres.sql`](packages/nimbusware_store/schema/postgres.sql), seed config from the repo (`nimbusware-config seed-from-repo`), Ollama hints, and write `.env`.

Model catalog maintenance (offline-first): `python scripts/sync_model_catalog.py --help`.

Or manually:

```bash
docker compose up -d postgres
cp .env.example .env
# Edit NIMBUSWARE_DATABASE_URL, NIMBUSWARE_ADMIN_TOKEN, etc.
poetry run nimbusware-config seed-from-repo
```

### 3. Run

**Desktop shell (API + Maker + pywebview):**

```bash
poetry run nimbusware-run
# or: python run.py
```

**Admin Console (separate window — admin token required at sign-in):**

```bash
poetry run nimbusware-admin
# or: poetry run nimbusware-run --admin
# or: python run.py --admin
```

**Maker app only (API must be running separately):**

```bash
poetry run nimbusware-maker
```

**Quick local dev (in-memory store, stub critics, no Postgres):**

```bash
poetry run nimbusware-run --quick
# or: poetry run nimbusware-maker --quick  (API must use same env — prefer nimbusware-run --quick)
```

**Launcher (install / update / run buttons):**

```bash
poetry run nimbusware-launcher
```

**Separate processes:**

```bash
poetry run nimbusware-api
# Web UIs (default when NIMBUSWARE_UI_BACKEND=web):
#   Maker:  http://127.0.0.1:8000/v1/maker/app/
#   Admin:  http://127.0.0.1:8000/v1/admin/app/
poetry run nimbusware-maker
poetry run nimbusware-admin
```

Smoke check (no GUI): `python run.py --smoke` or `python scripts/e2e_smoke.py`. Use `--admin --smoke` for the admin web entry.

API docs: http://127.0.0.1:8000/docs — operations are tagged **user** (Maker) vs **admin** (Admin Console) in OpenAPI.

Operator analytics: `GET /v1/platform/analytics/competitive-summary` and `GET /v1/platform/analytics/bundle-outcomes` (Admin **Metrics** tab); `GET /v1/platform/analytics/pressure-history` (Admin **Hardware** tab).

## User vs Admin

| Surface | Who | Auth |
|---------|-----|------|
| **Maker** (default) | End user / maker | No admin token for the product loop (`GET/POST /projects`, runs, maker approval) |
| **Admin Console** | Ops / dev / admin | Admin token at console sign-in; API admin routes use `X-Nimbusware-Admin-Token` (Individual) or `maker_admin` API key (Enterprise) |
| **Maker → Admin** | Admin on same machine | Maker shell **Admin console** link → `/v1/admin/app/` |

Enterprise IAM scopes on API keys:

| Scope | Use |
|-------|-----|
| `maker_user` | Maker app / user routes only |
| `maker_admin` | Admin Console + control-plane mutations (includes `maker_user`) |

Bootstrap (`POST /v1/enterprise/iam/bootstrap`) returns a **maker_admin** key. Create tenant user keys with `POST /v1/enterprise/tenants/{id}/api-keys` and `"api_scopes": ["maker_user"]`.

## Maker app

Web entry: `GET /v1/maker/app/` ([`packages/nimbusware_maker_web`](packages/nimbusware_maker_web/static/)). Launcher: `poetry run nimbusware-maker` or `poetry run nimbusware-run` (pywebview). Uses `NIMBUSWARE_API_BASE` (default `http://127.0.0.1:8000/v1`). Set `NIMBUSWARE_API_KEY` on Enterprise (user-scoped key).

**Home & onboarding**

- First-run wizard: folder → readiness → **fit-ranked model** → intent → create run (`GET /v1/platform/hardware` + ranked models)
- **Models** tab: three-step preset wizard (`GET /platform/models/ranked` → preset → `POST /platform/models/apply-preset`); Ollama pull unchanged
- Project picker backed by `nimbusware_project` (`GET/POST/PATCH /v1/projects` — **no admin token**; `DELETE` is admin-only)
- Per-project run history and **Settings** tab (hardware tier + resource governor sliders, Ollama model list, readiness presets, auto-advance hint)

**Chat** (default tab — `#/chat`)

- Primary Maker entry for attached projects: classify intent → confirm or override work type → start run or campaign
- Rules-first classifier (`nimbusware_maker.intent_classifier`) with optional LLM when `NIMBUSWARE_INTENT_CLASSIFIER_MODEL` is set; rules hard-override unsafe LLM routes
- **Work types:** `quick`, `patch`, `slice`, `campaign`, `factory` — mapped to workflow profiles (`quick_local`, `patch`, `micro_slice` or project default, `campaign_micro_slice`, `campaign_factory_zero_touch`); `work_type` + `work_type_source` (`classifier`, `operator_override`, `ide`) frozen on `run.created`
- Patch attachments: target paths, failing test, stack trace → `patch_context` on start; mid-run steering via `[steer]` interjection (chat) or Progress interjection ribbon
- APIs: `POST /v1/chat/sessions`, `POST /v1/chat/classify`, `POST /v1/chat/sessions/{id}/start`; MCP parity: `nimbusware_classify_intent`, `nimbusware_patch`, `nimbusware_interject` ([docs/ide-bridge.md](docs/ide-bridge.md)); ADR [020](docs/adr/020-unified-chat-work-type-routing.md)
- **Build** tab redirects to Chat for new runs; legacy Build flow remains available via API

**Build** (API / catalog)

- Plain-language business prompt → clarifying questions → `requirements` artifact on run create
- Runs attach to a project workspace (`project_id` on `POST /v1/runs`); executor resolves workspace from project metadata

**Progress**

- **Run theater** group chat on Progress tab (`GET /v1/runs/{id}/theater`, SSE `/theater/stream`, markdown export `/theater/export`); workflow `theater:` block frozen on `run.created` metadata
- Plain-language summaries (`GET /v1/runs/{id}/maker-progress`, SSE `/maker-progress/stream`); `resource_pressure` banner when governor throttles RAM
- Optional theater LLM one-liners: `NIMBUSWARE_THEATER_LLM_SUMMARY=1` or `theater.llm_summary` on `run.created` (off by default)
- Tabbed web UI: Home, **Chat** (default), Build (redirect), Review, Progress (SSE theater + maker-progress), Plan, Models, Settings; PWA manifest + offline service worker (`sw.js`) + Web Push registration when VAPID configured; `?run_id=` deep links

**v1.1 Maker UX**

- **Session hub** — per-project active `run_id` in `sessionStorage` (`session-hub.js`), URL `?run_id=` deep links, and `/runs?status=running` fallback; shared across Plan, Progress, and Review
- **Compaction theater** — compaction markers in run theater; revert via `POST /v1/runs/{id}/compactions/{compaction_id}/revert`
- **Findings** — blocking findings panel on Progress (HIGH/BLOCKER severity with repro steps)
- **Operator ribbons** — dev-env start/stop/regression, interjection Next/Last queue, autopilot slider (`GET/PUT /v1/runs/{id}/autopilot`), improvement/resolution council summary from timeline
- **Plan / completion** — Plan tab campaign backlog tree; factory tier + ISM coverage on maker-progress (`factory_status` projection); factory evidence JSON + zip export via `GET /v1/runs/{id}/factory-evidence` and `.../export`

**Review**

- Research brief approve/reject (`GET /v1/runs/{id}/research`, POST approve/reject); stitch panel (`GET /v1/runs/{id}/stitch-summary`)
- Plan approval and per-slice apply/skip with diff preview (`GET /v1/runs/{id}/maker/pending`, plan approve, slice prepare/apply/skip)
- Workspace revert to last snapshot (`POST /v1/runs/{id}/workspace/revert`)
- Approval mode sets `maker_approval.enabled` on runs with requirements; slice chain auto-advances by default — set `NIMBUSWARE_SLICE_AUTO_ADVANCE=0` to pause for manual approve/skip

**Admin console link**

- Maker shell header links to `/v1/admin/app/`; Admin routes still require `X-Nimbusware-Admin-Token` (or Enterprise API key) — opening Admin does not grant user-route admin headers on Maker API calls

## Admin Console

**Admin/dev only** — not part of the default product path. Web app: `GET /v1/admin/app/` ([`packages/nimbusware_admin_ui`](packages/nimbusware_admin_ui/)). Sign in with `NIMBUSWARE_ADMIN_TOKEN` (stored in browser `sessionStorage`). Uses `NIMBUSWARE_API_BASE` (default `http://127.0.0.1:8000/v1`).

Launch: `poetry run nimbusware-admin`, `nimbusware-run --admin`, or the launcher **Admin Console…** button. Build the SPA after UI changes: `cd packages/nimbusware_admin_ui && npm ci && npm run build`.

**Runs & timeline**

- Filtered run list (workflow profile, dates, escalation, status), pagination, CSV/JSON export
- Run detail: summary, append-only timeline, findings, live critic matrix, **run theater** panel (evidence expand, jump to timeline `store_seq`), **policy compare** (side-by-side frozen snapshots), **probation promotion notices**, **role execute (debug)** panel
- Lifecycle actions: retry, escalate; drill-downs for integrator gate, personas, agent evaluator, self-refinement, security scan, universal critique, scraper fetch, preflight

**Configuration & search**

- **Ollama models** — installed-model search, admin pull/delete, Maker user policy toggles (`ollama_user_policy` in `configs/model-routing.yaml`)
- Operator chat — start runs, steer workflow from the UI
- Custom agents — CRUD + system prompt editor (Postgres registry in DB mode)
- Bundle catalog search (local + API parity), FAISS index status, catalog editor
- Persona shelves and editor (overlap report, probation reliability thresholds), workflow explainers, integrator preview/apply
- **Blast radius** and **Critic packs** Config tabs (dry-run workflow impact, Postgres pack editor)
- Cross-run preflight trends and fleet metrics export

**Enterprise only** (Admin **Fleet** tab at `/v1/admin/app/fleet`): set Enterprise API key at sign-in, optional tenant switcher, fleet memory status, Ollama SLI + preflight aggregate, Redis worker health, hardware fleet tiers. Cross-run preflight **history** remains on the **Preflight** tab.

Run detail includes **Open in Maker Review** deep links (`NIMBUSWARE_MAKER_URL/?run_id=…`).

## Nimbusware API (`/v1`)

All routes are under `/v1` unless noted. OpenAPI groups operations as **user** (Maker) or **admin** (Admin Console); see `/docs`.

### Auth (Individual vs Enterprise)

| Route group | Individual | Enterprise |
|-------------|------------|------------|
| **User** (`user` tag) | Open on localhost | `X-Nimbusware-Api-Key` with `maker_user` scope |
| **Admin** (`admin` tag) | `X-Nimbusware-Admin-Token` | `maker_admin` scope or admin token (bootstrap) |

Enterprise routes require `NIMBUSWARE_EDITION=enterprise` and (except bootstrap) `X-Nimbusware-Api-Key`.

### Core (all editions)

| Area | Endpoints | Access |
|------|-----------|--------|
| **Runs** | `GET/POST /runs`, `GET /runs/{id}`, timeline, findings | User |
| **Maker progress** | `GET /runs/{id}/maker-progress`, SSE `.../maker-progress/stream` | User |
| **Run theater** | `GET /runs/{id}/theater`, SSE `.../theater/stream`, `GET .../theater/export` | User |
| **Maker web** | `GET /maker/app/` (PWA: Chat default, theater, research approve, slice approval) | User |
| **Chat** | `POST /chat/sessions`, `POST /chat/classify`, `POST /chat/sessions/{id}/start` | User |
| **Research / stitch** | `GET /runs/{id}/research`, POST `.../research/{brief_id}/approve|reject`, `GET /runs/{id}/stitch-summary` | User |
| **Maker approval** | `GET .../maker/pending`, plan approve, slice prepare/apply/skip, workspace revert | User |
| **Autopilot** | `GET/PUT /runs/{id}/autopilot` | User |
| **Dev environment** | `GET/POST /runs/{id}/dev-env/*` | User |
| **Interjection queue** | `GET/POST /runs/{id}/interjection-queue` | User |
| **Platform** | `GET /platform/edition`, `GET /platform/readiness`, `GET /platform/hardware`, `POST /platform/hardware/rescan` (`emit_event` + `run_id`), `GET /platform/analytics/stitch-outcomes`, `GET /platform/analytics/competitive-summary`, `GET /platform/analytics/bundle-outcomes`, `GET /platform/analytics/pressure-history` | User |
| **Model Manager** | `GET /platform/models/ranked`, `POST /platform/models/apply-preset`, `GET /platform/models/dependencies` | User |
| **Projects** | `GET/POST/PATCH /projects` | User |
| **Projects** | `DELETE /projects/{id}` | Admin |
| **Lifecycle** | `POST .../lifecycle/start`, `plan`, `verify`, `slice` | Admin |
| **Actions** | Retry, escalate | Admin |
| **Bundles** | `GET /bundles/search`, `GET /catalog` | User |
| **Bundles** | `PUT/PATCH /bundles/catalog`, `GET /bundles/catalog/source`, `GET /bundles/catalog-candidates` | Admin |
| **Critic packs** | `GET/PUT /config/critic-packs/{id}` | Admin (Postgres writes) |
| **Fleet critic reliability** | `GET /enterprise/fleet/critic-reliability` | Enterprise |
| **Personas** | Shelf read | User |
| **Personas** | Admin CRUD, `GET /personas/overlap-report` | Admin |
| **Admin BFF** | Run detail panels (`/admin/ui/runs/{id}/…`), fleet compare (`/admin/ui/enterprise/fleet-compare`), persona overlap (`/admin/ui/personas/overlap-report`) | Admin |
| **Custom agents** | `GET` list | User |
| **Custom agents** | `POST/PATCH/DELETE` | Admin |
| **Preflight** | `GET /preflight-history` | User |
| **Scraper artifacts** | Inventory | User |

### Enterprise

| Area | Endpoints | Notes |
|------|-----------|--------|
| **IAM** | `POST /enterprise/iam/bootstrap` (admin token), `GET /iam/me`, tenants, API keys | Bootstrap key has `maker_admin`; create `maker_user` keys per tenant |
| **Fleet memory** | `GET /status`, `POST /rebuild`, `GET /search`, `POST /sync` | Tenant-scoped org index |
| **Config NOTIFY** | `GET /enterprise/config-notify/status` | Listener status when enabled |
| **Object store** | `GET /enterprise/scraper-artifacts/object-store/status` | Primary backend config |
| **Fleet worker** | `GET /enterprise/fleet-worker/health`, `/metrics` | Redis queue depth, back-pressure |
| **Fleet Ollama SLI** | `GET /enterprise/fleet-ollama-sli/status`, `/preflight-aggregate` | Sustained p95 + history merge |

Admin header: `X-Nimbusware-Admin-Token` (from `NIMBUSWARE_ADMIN_TOKEN`). Enterprise user auth: `X-Nimbusware-Api-Key` with `maker_user` or `maker_admin` scope.

## CLI tools

| Command | Purpose |
|---------|---------|
| `poetry run nimbusware-api` | Start FastAPI/uvicorn |
| `poetry run nimbusware-config` | Import/export/seed Postgres config |
| `poetry run nimbusware-preflight` | Ad-hoc Ollama preflight probe + JSON histogram |
| `poetry run nimbusware-memory-index` | Build repo-scoped memory FAISS index |
| `poetry run nimbusware-memory-sync` | Enterprise fleet memory push/pull (canonical store) |
| `poetry run nimbusware-memory-replay` | Replay runs against memory fixtures |
| `poetry run nimbusware-role-telemetry` | Aggregate role telemetry from events |
| `poetry run nimbusware-routing-suggest` | Read-only `model-routing.yaml` suggestions |
| `poetry run nimbusware-run-worker` | Redis/in-memory run-dispatch worker |
| `poetry run nimbusware-fleet-ollama-sli` | Enterprise sustained Ollama p95 export job |
| `poetry run nimbusware-run` | Desktop API + Maker window (default) |
| `poetry run nimbusware-admin` | Desktop API + Admin Console window |
| `poetry run nimbusware-maker` | Start API + open Maker web UI (`/v1/maker/app/`); add `--quick` for in-memory solo dev |
| `poetry run nimbusware-git-pr` | Open GitHub PR for a Nimbusware run branch (`gh` CLI required) |
| `poetry run nimbusware-mcp` | Stdio MCP server for IDE run status, theater, slice diff, plan approve, chat classify/patch/interject ([`docs/ide-bridge.md`](docs/ide-bridge.md)) |
| `poetry run nimbusware-launcher` | Install/update/run launcher UI |

Scripts: [`scripts/build_bundle_faiss_index.py`](scripts/build_bundle_faiss_index.py), [`scripts/build_memory_faiss_index.py`](scripts/build_memory_faiss_index.py), [`scripts/run_dispatch_worker.py`](scripts/run_dispatch_worker.py), [`scripts/prune_scraper_artifacts.py`](scripts/prune_scraper_artifacts.py), [`scripts/e2e_smoke.py`](scripts/e2e_smoke.py).

Runbooks: [`scripts/run_dispatch_fleet_runbook.md`](scripts/run_dispatch_fleet_runbook.md), [`scripts/fleet_ollama_sli_runbook.md`](scripts/fleet_ollama_sli_runbook.md).

## Docker Compose

```bash
docker compose up -d postgres
# API container (Lane V4):
docker compose --profile api up -d api
# Enterprise Redis worker:
docker compose --profile fleet up -d redis
```

Set `NIMBUSWARE_RUN_DISPATCH=redis` and `NIMBUSWARE_REDIS_URL=redis://127.0.0.1:6379/0` for multi-worker verify dispatch.

Production packaging and K8s reference: [`docs/deploy/README.md`](docs/deploy/README.md) — API, Redis, schema Job, dispatch worker, optional Admin Console ([`docs/deploy/k8s/`](docs/deploy/k8s/)). Enterprise integrator gate: [`docs/deploy/enterprise-integrator-runbook.md`](docs/deploy/enterprise-integrator-runbook.md). Multi-host Redis fleet secrets: [`docs/deploy/production-fleet-redis-secrets.md`](docs/deploy/production-fleet-redis-secrets.md). Agent sandbox backends: [`docs/deploy/agent-sandbox.md`](docs/deploy/agent-sandbox.md). Enterprise OIDC console gate: [`docs/deploy/oidc.md`](docs/deploy/oidc.md). External fleet SLI: [`scripts/fleet_ollama_sli_runbook.md`](scripts/fleet_ollama_sli_runbook.md). SBOM: `.github/workflows/sbom.yml` on version tags (blocking on generation errors).

## Enterprise setup sketch

```powershell
$env:NIMBUSWARE_EDITION = "enterprise"
poetry run nimbusware-api
# Bootstrap (once, admin token) → maker_admin key:
# POST /v1/enterprise/iam/bootstrap  Header: X-Nimbusware-Admin-Token
# Use returned api_key as X-Nimbusware-Api-Key on subsequent /v1/* calls
#
# Create a Maker-only user key for a tenant:
# POST /v1/enterprise/tenants/{tenant_id}/api-keys
#   Body: { "label": "maker-user", "api_scopes": ["maker_user"] }
```

Configure fleet memory canonical store: `NIMBUSWARE_FLEET_MEMORY_STORE_URI` or `NIMBUSWARE_FLEET_MEMORY_STORE_DIR`. Enable config NOTIFY: `NIMBUSWARE_CONFIG_NOTIFY=1`. Object-store primary: `NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_PRIMARY=1` plus URL/bucket env vars (see `.env.example` and enterprise routes).

Enterprise APIs (read-only / ops): `GET /v1/enterprise/fleet/analytics/compare`, `GET /v1/config/blast-radius`, `GET /v1/enterprise/audit-export` (includes IAM, events, research index, egress audit), `GET /v1/enterprise/research-index`, `GET /v1/enterprise/egress-audit`. Buyer checklist: [docs/enterprise-buyer.md](docs/enterprise-buyer.md).

External chat (§20.5 boundary — not in-product workspace): `POST /v1/integrations/external-chat/webhook` with `NIMBUSWARE_WEBHOOK_SECRET` or admin token ([docs/integrations-external-chat.md](docs/integrations-external-chat.md)).

## Linux desktop (GTK / pywebview)

On Linux, `run.py` can install GTK/WebKit deps via `nimbusware_env.linux_desktop_deps`. Skip during install:

```bash
python scripts/install_nimbusware.py --skip-linux-desktop-deps
```

## Build launcher binary

**Windows:** `.\scripts\build_launcher.ps1` → `dist/NimbuswareLauncher.exe`  
**macOS / Linux:** `./scripts/build_launcher.sh` → `dist/NimbuswareLauncher`

Place the binary next to `pyproject.toml`. Build artifacts are gitignored.

## Operator journey tests (E2E extension)

Layered operator testing lives under `tests/e2e/` (**25** journey tests with `-m e2e`; one slow stack soak is opt-in). Playwright checks visible Build/Review/Progress/Settings controls via route activation (`tests/e2e/web/maker_route_helper.ts`); **31** tests in **21** spec files cover apply-slice, session hub, launch scorecard (per-dimension rows), Settings launch check, context artifact save/insert, integrator stitch ribbon, **operator ribbons** (dev-env, interjection, autopilot, variant arena), Admin launch scorecard + factory evidence, scoped compaction toolbar, multi-slice campaign progress, mobile theater parity, and full campaign+scorecard replay. Launch-eval parity rows map to specs via [`tests/web/parity_launch_wiring.yaml`](tests/web/parity_launch_wiring.yaml). Stack subprocess tests set `NIMBUSWARE_EMBED_DISPATCH_WORKER=1` so the API process drains the memory queue; long-run stack soak: [`scripts/e2e_stack_soak_runbook.md`](scripts/e2e_stack_soak_runbook.md) (weekly **stack-soak** job in [`.github/workflows/slow_tests.yml`](.github/workflows/slow_tests.yml)). Redis fleet dispatch soak: [`scripts/e2e_redis_fleet_soak_runbook.md`](scripts/e2e_redis_fleet_soak_runbook.md) (weekly **redis-fleet-soak** with dual Redis brokers via `NIMBUSWARE_REDIS_FLEET_URLS`). Persistent dev-env journey soak: [`scripts/run_dev_env_weekly_soak.py`](scripts/run_dev_env_weekly_soak.py) (weekly **dev-env-weekly-soak**). Integration tests with live Redis use `tests/integration/test_redis_dispatch_worker_stack.py` (`-m integration`). The default unit CI job runs the `slice.e2e` apply journey when `NIMBUSWARE_SLICE_E2E_COMMAND` is set. PR **e2e** job retries flaky journeys once (`--reruns 1`); weekly [`.github/workflows/e2e_flake_monitor.yml`](.github/workflows/e2e_flake_monitor.yml) re-runs the same Postgres e2e suite and opens an issue on failure.

| Layer | Location | CI |
|-------|----------|-----|
| L1 Journey API | `tests/e2e/journeys/` + `tests/e2e/harness/` | PR **e2e** job (`-m e2e`) |
| L2 Stack | `tests/e2e/harness/stack.py` | `-m "e2e_stack and integration"`; weekly stack-soak |
| L3 Web UI | `tests/e2e/web/` (Playwright) | PR **web** job |

```bash
poetry run pytest tests/e2e/journeys -m e2e_journey -q
poetry run python scripts/e2e_smoke.py --profile app --skip-install-check
```

Attachable fixture workspaces: `tests/fixtures/repos/tiny_python_app/` (includes micro-slice stub modules under `packages/nimbusware_orchestrator/`), `tiny_web_app/`, `tiny_broken_app/` (intentionally failing tests), `tiny_api_app/` (REST-style routes). Golden timelines: `tests/e2e/golden/timelines/` (`default_lifecycle`, `micro_slice_happy`, `micro_slice_web_apply`, `campaign_micro_slice_created`, `micro_slice_web_created`). Campaign golden timeline: `tests/fixtures/campaign/golden_multi_tick_timeline.json`. Redis fleet soak (ops): [`scripts/e2e_redis_fleet_soak_runbook.md`](scripts/e2e_redis_fleet_soak_runbook.md). Opt-in workflow with browser verify stage: [`configs/workflows/micro_slice_web.yaml`](configs/workflows/micro_slice_web.yaml). Eval tuning: [`docs/eval-tuning-guide.md`](docs/eval-tuning-guide.md).

## Launch eval (workspace quality)

Deterministic rubric v0 scores attached workspaces on maturity, maintainability, scalability, security, and testability. Campaign completion emits `launch_eval.completed` on the event timeline when the campaign passes, including `attach_context` (matched catalog `prompt_id`, workflow profile, business prompt) when the run originated from a catalog prompt.

```bash
poetry run python scripts/launch_eval.py path/to/workspace --json
poetry run python scripts/launch_eval.py path/to/workspace --json --llm   # opt-in Ollama findings
poetry run python scripts/launch_eval.py --matrix   # score all catalog default_workspaces
poetry run python scripts/launch_eval.py --run-id <uuid> --json   # Postgres attach + attach_context
poetry run python scripts/launch_eval.py --run-id <uuid> --run-events events.json --json
```

Maker API: `POST /v1/runs/{run_id}/maker/launch-eval` scores the attached workspace, emits `launch_eval.completed` on the timeline, and returns `attach_context` when the run matches a catalog prompt. The Maker Review tab **Run launch check** button triggers scoring; **Load scorecard** reads the latest timeline event. Maker **Settings** includes the same **Run launch check** action for any run ID. Admin **Run detail** includes the same **Run launch check** control and structured scorecard panel. Both UIs render aggregate + rubric dimensions (per-row `data-testid`) + optional LLM dimension rows when `NIMBUSWARE_LAUNCH_EVAL_LLM=1`.

Set `NIMBUSWARE_LAUNCH_EVAL_LLM=1` (or `--llm`) for Ollama-backed findings and optional per-dimension scores (`llm_dimensions` on the scorecard); optional `NIMBUSWARE_LAUNCH_EVAL_LLM_MODEL`. Default rubric stays deterministic when LLM is off or unreachable.

Prompt catalog: [`configs/launch_eval/prompts/`](configs/launch_eval/prompts/) and [`configs/launch_eval/catalog.yaml`](configs/launch_eval/catalog.yaml) (`basic_crm`, `todo_api`, `contacts_api`, `static_site`). Golden replay fixtures: [`tests/fixtures/launch_eval/`](tests/fixtures/launch_eval/) (workspace scorecards + campaign manifest with `crm`, `todo_api`, and `contacts_api` snapshots). Weekly CI runs `launch_eval.py --matrix` ([`.github/workflows/launch_eval.yml`](.github/workflows/launch_eval.yml)). Parity rows: Maker `launch_eval_scorecard`, `settings_launch_check`; Admin `launch_eval_scorecard_admin` — wired to Playwright in [`tests/web/parity_launch_wiring.yaml`](tests/web/parity_launch_wiring.yaml).

The `micro_slice_web` workflow profile enables `slice.e2e` during Maker apply when `NIMBUSWARE_SLICE_E2E_COMMAND` is set (or Playwright is on PATH).

## Testing

Layout and CI subsets: [`tests/README.md`](tests/README.md).

```bash
# Matches GitHub CI unit + web jobs (ruff, audit_operator_env, format, mypy, bandit, pip-audit, floors, pytest @ 75%; optional vitest + Playwright when node is installed):
./scripts/ci_check.ps1   # Windows
./scripts/ci_check.sh    # Linux/macOS (--skip-web to skip vitest/Playwright)

poetry run pytest tests/e2e/journeys -m e2e_journey -q
poetry run pytest tests/ -q
poetry run pytest tests/ -q -m "not integration and not slow and not benchmark"
poetry run pytest tests/benchmark/ -m benchmark --benchmark-only
```

Optional hooks: `pip install pre-commit && pre-commit install` (ruff, format, compileall, mypy via `scripts/mypy_ci_targets.py` tranches B–E).

Integration tests need `NIMBUSWARE_DATABASE_URL` (`@pytest.mark.integration`). Gates script: `scripts/run_integration_like_ci.ps1` / `.sh`.

## Configuration reference (common env vars)

Install-only variables stay in [`.env.example`](.env.example). Admin and Maker tunables are in Postgres — see [docs/operator-settings.md](docs/operator-settings.md).

| Variable | Scope | Purpose |
|----------|-------|---------|
| `NIMBUSWARE_DATABASE_URL` | install | Postgres for events + config |
| `NIMBUSWARE_REPO_ROOT` | install | Repo root for configs and artifacts |
| `NIMBUSWARE_ADMIN_TOKEN` | install | Admin Console + admin API |
| `NIMBUSWARE_API_BASE` | install | UI → API URL |
| `NIMBUSWARE_USE_LLM` | user | Enable LLM-backed stages (Maker Settings) |
| `NIMBUSWARE_SLICE_AUTO_ADVANCE` | user | Auto-advance micro-slices (Maker Settings) |
| `NIMBUSWARE_FILESYSTEM_JAIL` | user | Deny `.env`/`.git`/secrets paths for agent tools (default on) |
| `NIMBUSWARE_SANDBOX_BACKEND` | user | Agent shell sandbox: `none` (host+jail), `stub`, `docker` (Individual); `kubernetes` / `e2b` (Enterprise fleet). See [agent-sandbox.md](docs/deploy/agent-sandbox.md) |
| `NIMBUSWARE_SANDBOX_DOCKER_IMAGE` | user | Image for docker sandbox (default `python:3.11-slim`) |
| `NIMBUSWARE_FAST_SLICE` | user | Env override for workflow `fast_slice` opt-in |
| `NIMBUSWARE_PROBATION_AUTO_SHELVE` | user | Disable auto-shelve on probation reliability failure (unset = on) |
| `NIMBUSWARE_PROBATION_NOTIFY_BEFORE_PROMOTE` | user | Disable promotion notice finding (unset = on) |
| `NIMBUSWARE_HW_SSH_HOST` | install | Enterprise remote SSH hardware probe target |
| `NIMBUSWARE_HW_FLEET_HOSTS` | install | Comma-separated hosts for fleet hardware tier dashboard |
| `NIMBUSWARE_SLICE_BUDGET_PRESET` | user | Micro-slice budget: `tiny`, `standard`, or `careful` |
| `NIMBUSWARE_SLICE_E2E_COMMAND` | user | Custom command when workflow `slice.e2e.enabled` is true |
| `NIMBUSWARE_OIDC_ENABLED` | install | Enterprise Admin Console OIDC SSO gate |
| `NIMBUSWARE_AUDIT_RETENTION_DAYS` | install | Enterprise audit export retention window |
| `NIMBUSWARE_SKIP_PREFLIGHT` | system | Skip Ollama preflight (Admin / CI) |
| `NIMBUSWARE_RUN_DISPATCH` / `NIMBUSWARE_REDIS_URL` | install | Fleet worker dispatch |

Full catalog: `poetry run python scripts/audit_operator_env.py` (198+ keys).

## License

Nimbusware (including Nimbusware) is free software under the [GNU General Public License v3.0](LICENSE). Copyright © 2026 Nimbusware contributors.
