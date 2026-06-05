# Nimbusware

Nimbusware is a **local-first** platform for operating adversarial agentic software workflows. It combines a **FastAPI control plane**, **Maker** and **Admin** web apps (Alpine + Preact at `/v1/maker/app/` and `/v1/admin/app/`), optional **desktop shells** (pywebview), and local integration with the **Hermes** online agentic system (multi-role pipeline, unanimous gates, verifiers, and optional Ollama-backed LLM stages via `hermes_*` packages).

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
- **Fleet memory** — org-scoped index, canonical store sync (`hermes-memory-sync`), search API
- **Config NOTIFY** — Postgres `LISTEN/NOTIFY` + `config.document.updated` cache invalidation
- **Object-store primary** — S3-compatible scraper artifact backend (optional local mirror)
- **Redis fleet worker** — shared verify queue, health/back-pressure metrics
- **Fleet Ollama SLI** — sustained health p95 export + preflight aggregate API
- **Enterprise fleet (Admin)** — **Fleet** tab at `/v1/admin/app/fleet` (tenant switcher, fleet memory, Ollama SLI aggregate, worker health, hardware tiers; requires `X-Nimbusware-Api-Key` in Admin sign-in)

## Architecture

| Layer | Packages / entry | Role |
|-------|------------------|------|
| **Nimbusware API** | `nimbusware_api` | `/v1` REST, OpenAPI, Problem+JSON errors |
| **Maker app** | `nimbusware_maker` + `nimbusware_maker_web` | **User console** — web UI at `/v1/maker/app/` |
| **Admin Console** | `nimbusware_console` + `nimbusware_admin_ui` | **Admin/dev console** — web UI at `/v1/admin/app/` (Enterprise **Fleet** at `/v1/admin/app/fleet`) |
| **Agent tools** | `hermes_agent_tools` | Allowlisted tools; filesystem jail; sandbox (`none`/`stub`/`docker`/`kubernetes`/`e2b`); per-slice risk caps |
| **Hermes orchestrator** | `hermes_orchestrator`, `agent_core` | Run pipeline, critics, gates, slice chain, preflight |
| **Event store** | `hermes_store` | Append-only Postgres (or in-memory without DB URL) |
| **Config store** | `nimbusware_config` | Versioned Postgres documents + materializer (T1/T2) |
| **Memory** | `hermes_memory` | Repo-scoped retrieval index (Individual); fleet scope (Enterprise) |
| **IAM** | `nimbusware_iam` | Enterprise tenancy and API keys |
| **Extensions** | `hermes_extensions` | Personas, bundles, escalation, integrator helpers |
| **Research / stitch** | `hermes_research` | Research briefs, stitch stages, outcome analytics |
| **Projections** | `nimbusware_projections` | Pure event → timeline read models (no API import from orchestrator) |
| **UI HTTP client** | `nimbusware_client` | Shared Maker + Admin `/v1` client (Problem+JSON, auth headers) |
| **Desktop / env** | `nimbusware_env` | Edition gate, `env_flags`, admin token guards, desktop launchers |

Optional: **Ollama** for LLM stages (`HERMES_USE_LLM=1`), **Redis** for multi-worker dispatch, **FAISS** for bundle/memory vector search (`poetry install --with faiss`). **Pyright LSP** for slice symbol sketch ships with default `poetry install` (dev dependency); installer sets `HERMES_SLICE_LSP_ENABLED=1` in `.env`.

Environment prefixes: **`NIMBUSWARE_*`** (platform) and **`HERMES_*`** (agent runtime). Common toggles are centralized in [`packages/nimbusware_env/env_flags.py`](packages/nimbusware_env/env_flags.py). See [`.env.example`](.env.example).

Developer docs: [ARCHITECTURE.md](ARCHITECTURE.md) (canonical package map), [docs/README.md](docs/README.md) (doc index), [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [tests/README.md](tests/README.md). Operators: [bundle catalog promotion](docs/operator-bundle-catalog-promotion.md), [enterprise buyer checklist](docs/enterprise-buyer.md), [security CI gates](docs/security-quality-gates.md). Web UIs call `/v1` via `fetch` or `nimbusware_client`; Python display helpers use `packages/*/services/` (no direct HTTP in `*_display.py`).

## Hermes agent runtime (online system, local integration)

Capabilities below are provided by the Hermes agentic system; Nimbusware hosts the control plane and wires `hermes_orchestrator`, `hermes_store`, and related packages.

- **Run lifecycle** — `run.created` → plan → implement/verify paths with frozen `policy_snapshot` from materialized config
- **Adversarial critics** — domain-bound critique stages (security, performance, network/resilience, refactor on production profile)
- **Unanimous gates** — stage progression blocked until critics/verifiers pass (with escalation anti-deadlock)
- **Parallel writers** — frontend/backend writers with role taxonomy and failure routing
- **Bundle integrator** — catalog search, FAISS ranking, compatibility scoring, integrator gate
- **Personas** — business + development shelves, persona assignment, agent evaluator + persona coverage critic; **probation automation** (reliability auto-shelve, promote notice; `GET /v1/personas/{shelf}/{persona_id}/probation-reliability`)
- **Self-refinement** — gated/ungated loops with Phase D markers and optional LLM critique
- **Fast slice** (`fast_slice: true` or `HERMES_FAST_SLICE`) — skip optional universal critic matrix and slice LLM critique when max finding severity is below HIGH
- **Micro-slice workflow** (`workflow_profile=micro_slice`) — bounded files/LOC per slice (Maker preset `HERMES_SLICE_BUDGET_PRESET`: tiny / standard / careful), per-slice verify → critique → test → optional `slice.e2e` browser verify → gate, diff-aware replan, context packets, optional memory excerpt injection; maker runs auto-advance the slice chain by default (`HERMES_SLICE_AUTO_ADVANCE` unset or `1`; set `0` to pause for plan/slice approval)
- **Slice browser verify (`slice.e2e`)** — off by default (`slice.e2e.enabled: false` in [`configs/workflows/micro_slice.yaml`](configs/workflows/micro_slice.yaml)). Enable in workflow YAML or a copied profile; install Playwright (`poetry run playwright install`) or set `HERMES_SLICE_E2E_COMMAND` to a custom shell command. If the runner or `tests/e2e` is missing, the stage **SKIP**s and the slice gate still passes. PR CI does not install Playwright (see [CONTRIBUTING.md](CONTRIBUTING.md)).
- **Slice implement agent** — optional `HERMES_SLICE_IMPLEMENT=agent` path uses jail-bound allowlisted tools instead of a single-shot writer stub
- **Slice symbol sketch** — Pyright LSP `documentSymbol` by default (`HERMES_SLICE_LSP_ENABLED=1` after install; bundled via `poetry install`; override with `HERMES_SLICE_LSP_COMMAND`); AST fallback when LSP is off or unavailable
- **Preflight** — Ollama/model health at run start; CLI and fleet history APIs
- **Scraper stage** — role-gated HTTP fetch with on-disk or object-store artifacts and retention/prune tooling
- **Retrieval memory** — index findings/gate failures; replay harness; role telemetry and routing suggestions (read-only CLI)

Configs live under [`configs/`](configs/) (workflows, personas, roles, `model-routing.yaml` including `ollama_user_policy`, bundles, `critic_packs/`). With Postgres, operator edits persist to `nimbusware_config_document` and materialize at API startup (optional git export via `nimbusware-config`). Bundle catalog authority is YAML under the repo root unless `NIMBUSWARE_DATABASE_URL` is set, in which case `policy/bundle-catalog` in Postgres is authoritative (`GET /v1/bundles/catalog/source`).

## Benchmarks

Optional **SWE-bench-style** regression harness for the `micro_slice` workflow profile:

- Script: [`scripts/swe_bench_harness.py`](scripts/swe_bench_harness.py)
  - `--dry-run --json` — validate manifest + fixture layout
  - `--run --json` — score in-memory `micro_slice` pass against the fixture workspace (`slices_total`, `gates_passed`, `gates_failed`, `pass_rate`, `duration_sec`, `run_id`)
- Fixture: [`tests/fixtures/swe_bench/`](tests/fixtures/swe_bench/) (`min_pass_rate` in `manifest.json`)
- Published metrics: gitignored [`benchmarks/`](benchmarks/) — set `HERMES_SWE_BENCH_WRITE_JSON=1` to write `benchmarks/latest_swe_bench.json`
- CI: weekly [`.github/workflows/swe_bench.yml`](.github/workflows/swe_bench.yml) dry-run + **required** scored `--run` (`min_pass_rate: 1.0`); artifact `latest_swe_bench.json` (copy into `benchmarks/` for Admin Metrics)
- Env: `HERMES_SWE_BENCH_ENABLED`, `HERMES_SWE_BENCH_MANIFEST`, `HERMES_SWE_BENCH_WRITE_JSON`

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
  agent_core/           Event models and validation
  hermes_orchestrator/  Pipeline, critics, slice, preflight, dispatch
  hermes_store/         Postgres + in-memory event store
  hermes_memory/        Memory chunks, FAISS, fleet sync
  hermes_executor/      Role-gated outbound HTTP
  hermes_extensions/    Personas, bundles, catalog
  nimbusware_api/       FastAPI app
  nimbusware_maker/     Maker services, slice workflow, onboarding helpers
  nimbusware_maker_web/ Maker web UI static assets (Alpine)
  nimbusware_admin_ui/  Admin Preact SPA (built to dist/)
  nimbusware_hw/        Hardware probe, resource governor, model fit ranking
  nimbusware_console/   Admin display helpers + services (ops/dev)
  hermes_agent_tools/   Allowlisted agent tool runtime for slice implement
  nimbusware_config/    Config store + NOTIFY
  nimbusware_iam/       Enterprise IAM
  nimbusware_client/    Shared HTTP client for Maker + Admin UIs
  nimbusware_projections/  Timeline read-model helpers
  nimbusware_env/       Edition gate, env_flags, desktop runners
configs/                Workflow YAML, personas, bundles (seed / gitops review)
scripts/                Install, FAISS build, workers, e2e smoke, runbooks
tests/                  Pytest suite (unit/api/console/orchestrator/integration/e2e)
```

Generated/local paths are **gitignored** (`.cache/`, `.hermes/`, `configs/memory/`, `configs/bundles/index/`, `.env`).

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
# Installer also sets HERMES_SLICE_LSP_ENABLED=1 in .env (default; use --no-enable-slice-lsp to skip)
```

The installer can set up Poetry deps, Postgres (Docker or native), apply [`packages/hermes_store/schema/postgres.sql`](packages/hermes_store/schema/postgres.sql), seed config from the repo (`nimbusware-config seed-from-repo`), Ollama hints, and write `.env`.

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

Operator analytics snapshot: `GET /v1/platform/analytics/competitive-summary` (Admin **Metrics** tab).

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
- **Models** tab: Model Manager (hardware strip, ranked table, Quality/Balanced/Speed apply, dependency warnings)
- Project picker backed by `nimbusware_project` (`GET/POST/PATCH /v1/projects` — **no admin token**; `DELETE` is admin-only)
- Per-project run history and **Settings** tab (hardware tier + resource governor sliders, Ollama model list, readiness presets, auto-advance hint)

**Build**

- Plain-language business prompt → clarifying questions → `requirements` artifact on run create
- Runs attach to a project workspace (`project_id` on `POST /v1/runs`); executor resolves workspace from project metadata

**Progress**

- **Run theater** group chat on Progress tab (`GET /v1/runs/{id}/theater`, SSE `/theater/stream`, markdown export `/theater/export`); workflow `theater:` block frozen on `run.created` metadata
- Plain-language summaries (`GET /v1/runs/{id}/maker-progress`, SSE `/maker-progress/stream`); `resource_pressure` banner when governor throttles RAM
- Optional theater LLM one-liners: `HERMES_THEATER_LLM_SUMMARY=1` or `theater.llm_summary` on `run.created` (off by default)
- Tabbed web UI: Home, Build, Review, Progress (SSE theater + maker-progress), Models, Settings; PWA manifest; `?run_id=` deep links

**Review**

- Research brief approve/reject (`GET /v1/runs/{id}/research`, POST approve/reject); stitch panel (`GET /v1/runs/{id}/stitch-summary`)
- Plan approval and per-slice apply/skip with diff preview (`GET /v1/runs/{id}/maker/pending`, plan approve, slice prepare/apply/skip)
- Workspace revert to last snapshot (`POST /v1/runs/{id}/workspace/revert`)
- Approval mode sets `maker_approval.enabled` on runs with requirements; slice chain auto-advances by default — set `HERMES_SLICE_AUTO_ADVANCE=0` to pause for manual approve/skip

**Admin console link**

- Maker shell header links to `/v1/admin/app/`; Admin routes still require `X-Nimbusware-Admin-Token` (or Enterprise API key) — opening Admin does not grant user-route admin headers on Maker API calls

## Admin Console

**Admin/dev only** — not part of the default product path. Web app: `GET /v1/admin/app/` ([`packages/nimbusware_admin_ui`](packages/nimbusware_admin_ui/)). Sign in with `NIMBUSWARE_ADMIN_TOKEN` (stored in browser `sessionStorage`). Uses `NIMBUSWARE_API_BASE` (default `http://127.0.0.1:8000/v1`).

Launch: `poetry run nimbusware-admin`, `nimbusware-run --admin`, or the launcher **Admin Console…** button. Build the SPA after UI changes: `cd packages/nimbusware_admin_ui && npm ci && npm run build`.

**Runs & timeline**

- Filtered run list (workflow profile, dates, escalation, status), pagination, CSV/JSON export
- Run detail: summary, append-only timeline, findings, live critic matrix, **run theater** panel (evidence expand, jump to timeline `store_seq`)
- Lifecycle actions: retry, escalate; drill-downs for integrator gate, personas, agent evaluator, self-refinement, security scan, universal critique, scraper fetch, preflight

**Configuration & search**

- **Ollama models** — installed-model search, admin pull/delete, Maker user policy toggles (`ollama_user_policy` in `configs/model-routing.yaml`)
- Operator chat — start runs, steer workflow from the UI
- Custom agents — CRUD + system prompt editor (Postgres registry in DB mode)
- Bundle catalog search (local + API parity), FAISS index status, catalog editor
- Persona shelves and editor, workflow explainers, integrator preview/apply
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
| **Maker web** | `GET /maker/app/` (PWA: theater, research approve, slice approval) | User |
| **Research / stitch** | `GET /runs/{id}/research`, POST `.../research/{brief_id}/approve|reject`, `GET /runs/{id}/stitch-summary` | User |
| **Maker approval** | `GET .../maker/pending`, plan approve, slice prepare/apply/skip, workspace revert | User |
| **Platform** | `GET /platform/edition`, `GET /platform/readiness`, `GET /platform/hardware`, `POST /platform/hardware/rescan` (`emit_event` + `run_id`), `GET /platform/analytics/stitch-outcomes` | User |
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
| **Personas** | Admin CRUD | Admin |
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
| `poetry run hermes-preflight` | Ad-hoc Ollama preflight probe + JSON histogram |
| `poetry run hermes-memory-index` | Build repo-scoped memory FAISS index |
| `poetry run hermes-memory-sync` | Enterprise fleet memory push/pull (canonical store) |
| `poetry run hermes-memory-replay` | Replay runs against memory fixtures |
| `poetry run hermes-role-telemetry` | Aggregate role telemetry from events |
| `poetry run hermes-routing-suggest` | Read-only `model-routing.yaml` suggestions |
| `poetry run hermes-run-worker` | Redis/in-memory run-dispatch worker |
| `poetry run hermes-fleet-ollama-sli` | Enterprise sustained Ollama p95 export job |
| `poetry run nimbusware-run` | Desktop API + Maker window (default) |
| `poetry run nimbusware-admin` | Desktop API + Admin Console window |
| `poetry run nimbusware-maker` | Start API + open Maker web UI (`/v1/maker/app/`); add `--quick` for in-memory solo dev |
| `poetry run nimbusware-git-pr` | Open GitHub PR for a Hermes run branch (`gh` CLI required) |
| `poetry run nimbusware-mcp` | Stdio MCP server for IDE run status, theater, slice diff, plan approve ([`docs/ide-bridge.md`](docs/ide-bridge.md)) |
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

Set `HERMES_RUN_DISPATCH=redis` and `HERMES_REDIS_URL=redis://127.0.0.1:6379/0` for multi-worker verify dispatch.

Production packaging and K8s reference: [`docs/deploy/README.md`](docs/deploy/README.md) — API, Redis, schema Job, dispatch worker, optional Admin Console ([`docs/deploy/k8s/`](docs/deploy/k8s/)). Enterprise OIDC console gate: [`docs/deploy/oidc.md`](docs/deploy/oidc.md). External fleet SLI: [`scripts/fleet_ollama_sli_runbook.md`](scripts/fleet_ollama_sli_runbook.md). SBOM: `.github/workflows/sbom.yml` on version tags (blocking on generation errors).

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

Configure fleet memory canonical store: `NIMBUSWARE_FLEET_MEMORY_STORE_URI` or `NIMBUSWARE_FLEET_MEMORY_STORE_DIR`. Enable config NOTIFY: `NIMBUSWARE_CONFIG_NOTIFY=1`. Object-store primary: `HERMES_SCRAPER_ARTIFACT_OBJECT_STORE_PRIMARY=1` plus URL/bucket env vars (see `.env.example` and enterprise routes).

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

## Testing

Layout and CI subsets: [`tests/README.md`](tests/README.md).

```bash
# Matches GitHub CI (ruff, format, mypy via scripts/mypy_ci_targets.py, bandit, pip-audit, floors, pytest @ 75%):
./scripts/ci_check.ps1   # Windows
./scripts/ci_check.sh    # Linux/macOS

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
| `HERMES_USE_LLM` | user | Enable LLM-backed stages (Maker Settings) |
| `HERMES_SLICE_AUTO_ADVANCE` | user | Auto-advance micro-slices (Maker Settings) |
| `HERMES_FILESYSTEM_JAIL` | user | Deny `.env`/`.git`/secrets paths for agent tools (default on) |
| `HERMES_SANDBOX_BACKEND` | user | Agent shell sandbox: `none` (host+jail), `stub`, or `docker` (Individual v1; requires local Docker CLI) |
| `HERMES_SANDBOX_DOCKER_IMAGE` | user | Image for docker sandbox (default `python:3.11-slim`) |
| `HERMES_FAST_SLICE` | user | Env override for workflow `fast_slice` opt-in |
| `HERMES_PROBATION_AUTO_SHELVE` | user | Disable auto-shelve on probation reliability failure (unset = on) |
| `HERMES_PROBATION_NOTIFY_BEFORE_PROMOTE` | user | Disable promotion notice finding (unset = on) |
| `NIMBUSWARE_HW_SSH_HOST` | install | Enterprise remote SSH hardware probe target |
| `NIMBUSWARE_HW_FLEET_HOSTS` | install | Comma-separated hosts for fleet hardware tier dashboard |
| `HERMES_SLICE_BUDGET_PRESET` | user | Micro-slice budget: `tiny`, `standard`, or `careful` |
| `HERMES_SLICE_E2E_COMMAND` | user | Custom command when workflow `slice.e2e.enabled` is true |
| `NIMBUSWARE_OIDC_ENABLED` | install | Enterprise Admin Console OIDC SSO gate |
| `NIMBUSWARE_AUDIT_RETENTION_DAYS` | install | Enterprise audit export retention window |
| `HERMES_SKIP_PREFLIGHT` | system | Skip Ollama preflight (Admin / CI) |
| `HERMES_RUN_DISPATCH` / `HERMES_REDIS_URL` | install | Fleet worker dispatch |

Full catalog: `poetry run python scripts/audit_operator_env.py` (155+ keys).

## License

Nimbusware (including Hermes) is free software under the [GNU General Public License v3.0](LICENSE). Copyright © 2026 Nimbusware contributors.
