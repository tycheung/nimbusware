# Nimbusware

Nimbusware is a local-first platform for operating agentic software workflows. It includes the **Nimbusware API** and operator console (product layer) and the **Hermes** orchestration agent (`packages/hermes_*`, `agent_core`: event store, critics, gates, verifiers, LLM stages).

Current package version: `0.5.0`.

## Architecture

| Layer | Role |
|-------|------|
| **Nimbusware** | Product: desktop launcher, operator console, install/update flow |
| **Hermes agent** | Orchestration engine in `packages/hermes_*` and `agent_core` |
| **Postgres** | Append-only event store and config documents (when `NIMBUSWARE_DATABASE_URL` is set) |
| **Ollama** (optional) | Local LLM for plan/critique/evaluator branches when `HERMES_USE_LLM=1` |

Platform settings use the `NIMBUSWARE_*` prefix; agent runtime knobs use `HERMES_*` (see `.env.example`).

## What Runs in This Repo

- **Nimbusware API**: `packages/nimbusware_api` (`poetry run nimbusware-api`)
- **Operator console**: `packages/nimbusware_console/app.py` (Streamlit)
- **Desktop run shell**: `run.py` / `poetry run nimbusware-run` (API + Streamlit in pywebview)
- **Desktop launcher**: `launcher.py` / `poetry run nimbusware-launcher` (install / update / run)

Default workflow profile for new runs: `nimbusware_production`.

## Quick Start

### 1) Install dependencies

```bash
poetry install
```

### 2) Configure environment

Copy `.env.example` to `.env`:

- `NIMBUSWARE_DATABASE_URL` — Postgres for events/config
- `NIMBUSWARE_ADMIN_TOKEN` — admin API mutations (`X-Nimbusware-Admin-Token` header)
- `HERMES_USE_LLM=1` — enable Ollama-backed Hermes agent stages

### 3) Run Nimbusware

#### Option A: Desktop shell (recommended)

```bash
python run.py
# or
poetry run nimbusware-run
```

Starts:

- Nimbusware API on `127.0.0.1:${PORT:-8000}` (localhost only)
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
- **Install / setup** — `scripts/install_nimbusware.py` (Poetry, Postgres, optional seed)
- **Run Nimbusware** — launches `run.py`

#### Option C: Separate processes

```bash
poetry run nimbusware-api
poetry run streamlit run packages/nimbusware_console/app.py
```

## Smoke Test

No GUI window:

```bash
python run.py --smoke
```

Checks Streamlit `/_stcore/health` and API `/openapi.json`.

## Streamlit Operator Console

Single-page ops dashboard (`packages/nimbusware_console/app.py`):

- **Recent runs** — filters, pagination, CSV/JSON export
- **Run detail** — summary, timeline, findings, critic matrix, retry/escalate actions
- **Timeline drill-downs** — integrator gate, persona assignment, agent evaluator, self-refinement, security scan, universal critique, escalations, scraper fetch, preflight
- **Config tooling** — bundle catalog + FAISS, persona shelves/editor, workflow explainers, module integrator preview/apply

The UI talks to the Nimbusware API over `NIMBUSWARE_API_BASE` (default `http://127.0.0.1:8000/v1`).

## Nimbusware API (`/v1`)

Routers in `packages/nimbusware_api/app.py`:

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

On Linux, `run.py` can install GTK/WebKit deps automatically (`packages/nimbusware_env/linux_desktop_deps.py`). Skip during install:

```bash
python scripts/install_nimbusware.py --skip-linux-desktop-deps
```

## Build Launcher Binary

Platform-specific; build on each target OS.

**Windows**

```powershell
.\scripts\build_launcher.ps1
```

→ `dist/NimbuswareLauncher.exe` (temp files stay under `build/` and `dist/`, both gitignored)

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

## Repo Notes

- `.hermes/` — Hermes agent run artifacts (integration adapter workspaces); gitignored
- `HERMES_*` — agent runtime configuration (LLM, critics, scanners, slice orchestration)
- `NIMBUSWARE_*` — platform configuration (database, API URL, admin token, default workflow profile)
