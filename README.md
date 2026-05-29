# Nimbusware

Nimbusware is a local-first platform for operating agentic software workflows. It ships with the **Hermes** orchestration agent (FastAPI control plane, event store, critics, gates, and verifiers) plus operator tooling around it.

Current package version: `0.5.0`.

## Architecture

| Layer | Role |
|-------|------|
| **Nimbusware** | Product: desktop launcher, operator console, install/update flow |
| **Hermes agent** | Orchestration engine in `packages/hermes_*` and `agent_core` |
| **Postgres** | Append-only event store and config documents (when `HERMES_DATABASE_URL` is set) |
| **Ollama** (optional) | Local LLM for plan/critique/evaluator branches when `HERMES_USE_LLM=1` |

Environment variables still use the `HERMES_` prefix because they configure the Hermes agent runtime, not the whole monorepo name.

## What Runs in This Repo

- **Hermes API**: `packages/hermes_api` (`poetry run hermes-api`)
- **Operator console**: `packages/hermes_console/app.py` (Streamlit)
- **Desktop run shell**: `run.py` / `poetry run nimbusware-run` (API + Streamlit in pywebview)
- **Desktop launcher**: `launcher.py` / `poetry run nimbusware-launcher` (install / update / run)

Default workflow profile for new runs: `hermes_production`.

## Quick Start

### 1) Install dependencies

```bash
poetry install
```

### 2) Configure environment

Copy `.env.example` to `.env`:

- `HERMES_DATABASE_URL` — Postgres for events/config
- `HERMES_ADMIN_TOKEN` — admin API mutations (`X-Hermes-Admin-Token` header)
- `HERMES_USE_LLM=1` — enable Ollama-backed Hermes agent stages

### 3) Run Nimbusware

#### Option A: Desktop shell (recommended)

```bash
python run.py
# or
poetry run nimbusware-run
```

Starts:

- Hermes API on `127.0.0.1:${PORT:-8000}` (localhost only)
- Streamlit console on a local port
- pywebview window (no separate browser tab)

#### Option B: Launcher UI

```bash
python launcher.py
# or
poetry run nimbusware-launcher
```

Buttons:

- **Check for updates** — `git fetch` + compare to upstream
- **Update (git pull)** — `git pull --ff-only`
- **Install / setup** — `scripts/install_hermes.py` (Poetry, Postgres, optional seed)
- **Run Nimbusware** — launches `run.py`

#### Option C: Separate processes

```bash
poetry run hermes-api
poetry run streamlit run packages/hermes_console/app.py
```

## Smoke Test

No GUI window:

```bash
python run.py --smoke
```

Checks Streamlit `/_stcore/health` and API `/openapi.json`.

## Streamlit Operator Console

Single-page ops dashboard (`packages/hermes_console/app.py`):

- **Recent runs** — filters, pagination, CSV/JSON export
- **Run detail** — summary, timeline, findings, critic matrix, retry/escalate actions
- **Timeline drill-downs** — integrator gate, persona assignment, agent evaluator, self-refinement, security scan, universal critique, escalations, scraper fetch, preflight
- **Config tooling** — bundle catalog + FAISS, persona shelves/editor, workflow explainers, module integrator preview/apply

The UI talks to the Hermes API over `HERMES_API_BASE` (default `http://127.0.0.1:8000/v1`).

## Hermes API (`/v1`)

Routers in `packages/hermes_api/app.py`:

| Router | Purpose |
|--------|---------|
| runs | Create/list runs, timeline, findings |
| actions | Retry, escalate, role execute stub |
| bundles | Search, catalog read/write |
| personas | Shelf catalog; admin CRUD |
| preflight | Fleet preflight history |
| scraper-artifacts | On-disk artifact inventory |

OpenAPI: http://127.0.0.1:8000/openapi.json

## Linux Desktop (GTK / pywebview)

On Linux, `run.py` can install GTK/WebKit deps automatically (`packages/hermes_env/linux_desktop_deps.py`). Skip during install:

```bash
python scripts/install_hermes.py --skip-linux-desktop-deps
```

## Build Launcher Binary

Platform-specific; build on each target OS.

**Windows**

```powershell
.\scripts\build_launcher.ps1
```

→ `dist/NimbuswareLauncher.exe`

**macOS / Linux**

```bash
chmod +x scripts/build_launcher.sh
./scripts/build_launcher.sh
```

→ `dist/NimbuswareLauncher`

Place the binary in the repo root (next to `pyproject.toml`).

## Testing

```bash
poetry run pytest tests -q
```

## Naming convention

| Term | Use for |
|------|---------|
| **Nimbusware** | Product and repository: desktop launcher, operator console, install/update flow, PyInstaller `NimbuswareLauncher` |
| **Hermes** / **Hermes agent** | Orchestration subsystem: `packages/hermes_*`, `agent_core`, LLM stage prompts, `.hermes/` artifacts |
| **Hermes API** | HTTP control plane in `hermes_api` (`/v1`, `poetry run hermes-api`) |

**Intentionally unchanged (compatibility):** Python package names (`hermes_api`, …), Poetry scripts `hermes-*`, `HERMES_*` env vars, `X-Hermes-Admin-Token`, Postgres role/db `hermes`, workflow profile `hermes_production`, install script filenames (`install_hermes.py`).

**Preferred for new docs and UX:** `nimbusware-run`, `nimbusware-launcher`, and “Nimbusware” for anything that is not specifically the agent runtime.

## Repo Notes

- `.hermes/` — local Hermes agent run artifacts (integration adapter workspaces); gitignored
- `HERMES_*` env vars — Hermes agent configuration; retained for compatibility
