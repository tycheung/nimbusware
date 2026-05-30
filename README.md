# Nimbusware

Nimbusware is a **local-first** platform for operating adversarial agentic software workflows. It combines a **FastAPI control plane**, a **Streamlit Maker app** (the default product UI — business prompt → scoped projects → reviewable slice builds), an **Admin Console** for ops/dev control-plane work, optional **desktop shells**, and the **Hermes** orchestration engine (multi-role pipeline, unanimous gates, verifiers, and optional Ollama-backed LLM stages).

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
- **Enterprise console** — sidebar tenant switcher, fleet memory / preflight / worker dashboards

## Architecture

| Layer | Packages / entry | Role |
|-------|------------------|------|
| **Nimbusware API** | `nimbusware_api` | `/v1` REST, OpenAPI, Problem+JSON errors |
| **Maker app** | `nimbusware_maker` | **User console** — projects, intent, plain progress, slice approval/revert (no admin token for the product loop) |
| **Admin Console** | `nimbusware_console` | **Admin/dev console** — runs, timeline, config editors, fleet panels (admin token at sign-in) |
| **Agent tools** | `hermes_agent_tools` | Allowlisted read/grep/write/shell for slice implement agent mode |
| **Hermes orchestrator** | `hermes_orchestrator`, `agent_core` | Run pipeline, critics, gates, slice chain, preflight |
| **Event store** | `hermes_store` | Append-only Postgres (or in-memory without DB URL) |
| **Config store** | `nimbusware_config` | Versioned Postgres documents + materializer (T1/T2) |
| **Memory** | `hermes_memory` | Repo-scoped retrieval index (Individual); fleet scope (Enterprise) |
| **IAM** | `nimbusware_iam` | Enterprise tenancy and API keys |
| **Extensions** | `hermes_extensions` | Personas, bundles, escalation, integrator helpers |
| **Desktop** | `nimbusware_env` | `nimbusware-run` → Maker (default); `nimbusware-admin` → Admin Console; `nimbusware-launcher` |

Optional: **Ollama** for LLM stages (`HERMES_USE_LLM=1`), **Redis** for multi-worker dispatch, **FAISS** for bundle/memory vector search (`poetry install --with faiss`).

Environment prefixes: **`NIMBUSWARE_*`** (platform) and **`HERMES_*`** (agent runtime). See [`.env.example`](.env.example).

## Hermes orchestration (what the engine does)

- **Run lifecycle** — `run.created` → plan → implement/verify paths with frozen `policy_snapshot` from materialized config
- **Adversarial critics** — domain-bound critique stages (security, performance, network/resilience, refactor on production profile)
- **Unanimous gates** — stage progression blocked until critics/verifiers pass (with escalation anti-deadlock)
- **Parallel writers** — frontend/backend writers with role taxonomy and failure routing
- **Bundle integrator** — catalog search, FAISS ranking, compatibility scoring, integrator gate
- **Personas** — business + development shelves, persona assignment, agent evaluator + persona coverage critic
- **Self-refinement** — gated/ungated loops with Phase D markers and optional LLM critique
- **Micro-slice workflow** (`workflow_profile=micro_slice`) — bounded files/LOC per slice, per-slice verify → critique → test → gate, diff-aware replan, context packets, optional memory excerpt injection; maker runs pause for plan/slice approval unless auto-advance is enabled
- **Slice implement agent** — optional `HERMES_SLICE_IMPLEMENT=agent` path uses allowlisted tools instead of a single-shot writer stub
- **Preflight** — Ollama/model health at run start; CLI and fleet history APIs
- **Scraper stage** — role-gated HTTP fetch with on-disk or object-store artifacts and retention/prune tooling
- **Retrieval memory** — index findings/gate failures; replay harness; role telemetry and routing suggestions (read-only CLI)

Configs live under [`configs/`](configs/) (workflows, personas, roles, model-routing, bundles). With Postgres, operator edits persist to `hermes_config_document` and materialize at API startup (optional git export via `nimbusware-config`).

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
  nimbusware_maker/     Maker Streamlit UI + project store helpers
  nimbusware_console/   Admin Console Streamlit UI (ops/dev)
  hermes_agent_tools/   Allowlisted agent tool runtime for slice implement
  nimbusware_config/    Config store + NOTIFY
  nimbusware_iam/       Enterprise IAM
  nimbusware_env/       Edition gate, desktop runners
configs/                Workflow YAML, personas, bundles (seed / gitops review)
scripts/                Install, FAISS build, workers, e2e smoke, runbooks
tests/                  Pytest suite (~2,436 tests; unit/api/console/orchestrator/integration)
```

Generated/local paths are **gitignored** (`.cache/`, `.hermes/`, `configs/memory/`, `configs/bundles/index/`, `.env`).

## Quick start

### 1. Dependencies

```bash
poetry install
# Optional:
poetry install --with faiss    # bundle + memory FAISS indexes
poetry install --with redis    # Enterprise Redis dispatch (included for --edition enterprise)
```

### 2. Bootstrap (recommended)

```bash
python scripts/install_nimbusware.py
# Enterprise:
python scripts/install_nimbusware.py --edition enterprise
```

The installer can set up Poetry deps, Postgres (Docker or native), apply [`packages/hermes_store/schema/postgres.sql`](packages/hermes_store/schema/postgres.sql), seed config from the repo (`nimbusware-config seed-from-repo`), Ollama hints, and write `.env`.

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

**Launcher (install / update / run buttons):**

```bash
poetry run nimbusware-launcher
```

**Separate processes:**

```bash
poetry run nimbusware-api
poetry run streamlit run packages/nimbusware_maker/app.py
# Admin Console (admin token at load):
poetry run streamlit run packages/nimbusware_console/app.py
```

Smoke check (no GUI): `python run.py --smoke` or `python scripts/e2e_smoke.py`. Use `--admin --smoke` to smoke the Admin Console instead.

API docs: http://127.0.0.1:8000/docs — operations are tagged **user** (Maker) vs **admin** (Admin Console) in OpenAPI.

## User vs Admin

| Surface | Who | Auth |
|---------|-----|------|
| **Maker** (default) | End user / maker | No admin token for the product loop (`GET/POST /projects`, runs, maker approval) |
| **Admin Console** | Ops / dev / admin | Admin token at console sign-in; API admin routes use `X-Nimbusware-Admin-Token` (Individual) or `maker_admin` API key (Enterprise) |
| **Maker → Admin** | Admin on same machine | Sidebar **Sign in as admin** → **Open Admin Console** |

Enterprise IAM scopes on API keys:

| Scope | Use |
|-------|-----|
| `maker_user` | Maker app / user routes only |
| `maker_admin` | Admin Console + control-plane mutations (includes `maker_user`) |

Bootstrap (`POST /v1/enterprise/iam/bootstrap`) returns a **maker_admin** key. Create tenant user keys with `POST /v1/enterprise/tenants/{id}/api-keys` and `"api_scopes": ["maker_user"]`.

## Maker app

Streamlit entry: [`packages/nimbusware_maker/app.py`](packages/nimbusware_maker/app.py). Uses `NIMBUSWARE_API_BASE` (default `http://127.0.0.1:8000/v1`). Set `NIMBUSWARE_API_KEY` on Enterprise (user-scoped key).

**Home & onboarding**

- First-run wizard checks local readiness (Postgres, Ollama hints, workspace paths) via `GET /v1/platform/readiness`
- Project picker backed by `hermes_project` (`GET/POST /v1/projects` — **no admin token**; `DELETE` is admin-only)
- Per-project run history and **Settings** tab (model presets, auto-advance hint)

**Build**

- Plain-language business prompt → clarifying questions → `requirements` artifact on run create
- Runs attach to a project workspace (`project_id` on `POST /v1/runs`); executor resolves workspace from project metadata

**Progress**

- Plain-language stage summaries via `GET /v1/runs/{id}/maker-progress` (projection over run events)

**Review**

- Plan approval and per-slice apply/skip with diff preview (`GET /v1/runs/{id}/maker/pending`, plan approve, slice prepare/apply/skip)
- Workspace revert to last snapshot (`POST /v1/runs/{id}/workspace/revert`)
- Approval mode sets `maker_approval.enabled` on runs with requirements; disable auto chain with `HERMES_SLICE_AUTO_ADVANCE=0`

**Admin unlock (optional)**

- Sidebar **Sign in as admin** unlocks Advanced mode and **Open Admin Console** (does not grant user-route admin headers)

## Admin Console

**Admin/dev only** — not part of the default product path. Streamlit app: [`packages/nimbusware_console/app.py`](packages/nimbusware_console/app.py). Requires admin token at load. Uses `NIMBUSWARE_API_BASE` (default `http://127.0.0.1:8000/v1`).

Launch: `poetry run nimbusware-admin`, `nimbusware-run --admin`, or the launcher **Admin Console…** button.

**Runs & timeline**

- Filtered run list (workflow profile, dates, escalation, status), pagination, CSV/JSON export
- Run detail: summary, append-only timeline, findings, live critic matrix
- Lifecycle actions: retry, escalate; drill-downs for integrator gate, personas, agent evaluator, self-refinement, security scan, universal critique, scraper fetch, preflight

**Configuration & search**

- Operator chat — start runs, steer workflow from the UI
- Custom agents — CRUD + system prompt editor (Postgres registry in DB mode)
- Bundle catalog search (local + API parity), FAISS index status, catalog editor
- Persona shelves and editor, workflow explainers, integrator preview/apply
- Cross-run preflight trends and fleet metrics export

**Enterprise only** (sidebar): API key connect, tenant switcher, **Enterprise fleet dashboard** (fleet memory status, Ollama SLI + preflight aggregate, Redis worker health).

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
| **Maker progress** | `GET /runs/{id}/maker-progress` | User |
| **Maker approval** | plan approve, slice prepare/apply/skip, `POST /runs/{id}/workspace/revert` | User |
| **Projects** | `GET/POST /projects` | User |
| **Projects** | `DELETE /projects/{id}` | Admin |
| **Platform** | `GET /platform/edition`, `GET /platform/readiness` | User |
| **Lifecycle** | `POST .../lifecycle/start`, `plan`, `verify`, `slice` | Admin |
| **Actions** | Retry, escalate | Admin |
| **Bundles** | `GET /bundles/search`, `GET /catalog` | User |
| **Bundles** | `PUT/PATCH /bundles/catalog` | Admin |
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
| `poetry run nimbusware-maker` | Streamlit Maker only (expects API at `NIMBUSWARE_API_BASE`) |
| `poetry run nimbusware-launcher` | Install/update/run launcher UI |

Scripts: [`scripts/build_bundle_faiss_index.py`](scripts/build_bundle_faiss_index.py), [`scripts/build_memory_faiss_index.py`](scripts/build_memory_faiss_index.py), [`scripts/run_dispatch_worker.py`](scripts/run_dispatch_worker.py), [`scripts/prune_scraper_artifacts.py`](scripts/prune_scraper_artifacts.py), [`scripts/e2e_smoke.py`](scripts/e2e_smoke.py).

Runbooks: [`scripts/run_dispatch_fleet_runbook.md`](scripts/run_dispatch_fleet_runbook.md), [`scripts/fleet_ollama_sli_runbook.md`](scripts/fleet_ollama_sli_runbook.md).

## Docker Compose

```bash
docker compose up -d postgres
# Enterprise Redis worker:
docker compose --profile fleet up -d redis
```

Set `HERMES_RUN_DISPATCH=redis` and `HERMES_REDIS_URL=redis://127.0.0.1:6379/0` for multi-worker verify dispatch.

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

```bash
poetry run pytest tests/ -q
# CI-style unit subset (no Postgres integration, no slow tests):
poetry run pytest tests/ -q -m "not integration and not slow"
# Optional fleet benchmarks:
poetry run pytest tests/benchmark/ -m benchmark --benchmark-only
```

Install optional local hooks: `pip install pre-commit && pre-commit install` (runs ruff + whitespace checks).

Integration tests need `NIMBUSWARE_DATABASE_URL` (`@pytest.mark.integration`). Gates script: `scripts/run_integration_like_ci.ps1` / `.sh`.

## Configuration reference (common env vars)

| Variable | Purpose |
|----------|---------|
| `NIMBUSWARE_REPO_ROOT` | Repo root for configs and artifacts |
| `NIMBUSWARE_DATABASE_URL` | Postgres for events + config |
| `NIMBUSWARE_API_BASE` | UI → API URL |
| `NIMBUSWARE_API_KEY` | Enterprise Maker user key (`maker_user` scope) |
| `NIMBUSWARE_UI` | Desktop shell: `maker` (default) or `admin` / `console` |
| `NIMBUSWARE_ADMIN_TOKEN` | Admin Console sign-in + admin API routes; default dev value in `.env.example` — search `SEARCH_AND_REPLACE_BEFORE_PROD` before production |
| `NIMBUSWARE_ADMIN_CONSOLE_URL` | Maker sidebar link target for Open Admin Console (default `http://127.0.0.1:8502`) |
| `NIMBUSWARE_MAKER_URL` | Admin Console deep link back to Maker (default `http://127.0.0.1:8501`) |
| `NIMBUSWARE_EDITION` | `individual` (default) or `enterprise` |
| `HERMES_SKIP_PREFLIGHT` | Skip Ollama preflight (tests/CI) |
| `HERMES_USE_LLM` | Enable LLM-backed stages |
| `HERMES_SLICE_AUTO_ADVANCE` | `0` pauses micro-slice chain for maker approval |
| `HERMES_SLICE_IMPLEMENT` | Set to `agent` for allowlisted tool-based slice implement |
| `HERMES_RUN_DISPATCH` | `redis` or in-memory queue for workers |
| `HERMES_REDIS_URL` | Redis URL when dispatch=redis |

Full list: [`.env.example`](.env.example).

## License

See repository license file if present; otherwise treat as private/unlicensed until stated.
