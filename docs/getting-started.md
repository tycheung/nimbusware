# Getting started

## Prerequisites

- Python **>=3.10** (3.11+ recommended)
- [Poetry](https://python-poetry.org/) for dependencies

```bash
poetry install
# Optional extras:
poetry install --with faiss    # bundle + memory FAISS indexes
poetry install --with redis    # Enterprise Redis dispatch
```

## Bootstrap (recommended)

**Clone + quick demo** (no Postgres):

```bash
python scripts/install_nimbusware.py --clone <repo-url> --target-dir ./Nimbusware --non-interactive --skip-postgres
cd Nimbusware && poetry run nimbusware-run --quick
```

**From an existing clone:**

```bash
python scripts/install_nimbusware.py
python scripts/install_nimbusware.py --edition enterprise   # multi-tenant IAM, fleet
python scripts/install_nimbusware.py --install-profile barebones   # no Ollama download
```

The installer can set up Poetry deps, Postgres (Docker or native), schema, config seed, Ollama hints, and `.env`. See [install-profiles.md](install-profiles.md) and [model-hub.md](model-hub.md) for LLM setup after install.

**Manual path:**

```bash
docker compose up -d postgres
cp .env.example .env
# Edit NIMBUSWARE_DATABASE_URL, NIMBUSWARE_ADMIN_TOKEN, etc.
poetry run nimbusware-config seed-from-repo
```

Install timing targets: [deploy/first-install-timing.md](deploy/first-install-timing.md).

## Run

| Goal | Command |
|------|---------|
| Desktop (API + Maker) | `poetry run nimbusware-run` |
| Quick dev (in-memory, stub critics) | `poetry run nimbusware-run --quick` |
| Admin Console | `poetry run nimbusware-admin` |
| API only | `poetry run nimbusware-api` |
| Launcher UI | `poetry run nimbusware-launcher` |

**URLs** (default API on port 8000):

- Maker: `http://127.0.0.1:8000/v1/maker/app/`
- Admin: `http://127.0.0.1:8000/v1/admin/app/`
- OpenAPI: `http://127.0.0.1:8000/docs`

Smoke check (no GUI): `python run.py --smoke`

## Maker onboarding

After install, open **Maker Home** (`/v1/maker/app/#/home`):

1. **Readiness** — fix red/yellow checks (quick mode, Ollama, model pull).
2. **Three intents** — *Fix a bug*, *Build a feature*, *Build an app* — route to Chat with the right work type.
3. **Quick demo** — `poetry run nimbusware-run --quick` for in-memory store without Postgres.
4. **Factory demos** — catalog cards deep-link Chat with `campaign_factory_zero_touch`.

## Docker Compose

```bash
docker compose up -d postgres
docker compose --profile api up -d api      # API container
docker compose --profile fleet up -d redis  # Enterprise worker
```

Set `NIMBUSWARE_RUN_DISPATCH=redis` and `NIMBUSWARE_REDIS_URL` for multi-worker dispatch. Production packaging: [deploy/README.md](deploy/README.md).

## Linux desktop

`run.py` can install GTK/WebKit deps via `nimbusware_env.linux_desktop_deps`. Skip during install:

```bash
python scripts/install_nimbusware.py --skip-linux-desktop-deps
```

## Launcher binary

**Windows:** `.\scripts\publish\build_launcher.ps1` → `dist/NimbuswareLauncher.exe`  
**macOS / Linux:** `./scripts/publish/build_launcher.sh` → `dist/NimbuswareLauncher`

Place the binary next to `pyproject.toml`, or run it standalone — **Quick setup** clones or downloads source (git or GitHub zip) and runs the barebones install profile; **Full setup** adds Docker Postgres and Ollama when available.

## Enterprise sketch

```powershell
$env:NIMBUSWARE_EDITION = "enterprise"
poetry run nimbusware-api
# Bootstrap once with X-Nimbusware-Admin-Token → POST /v1/enterprise/iam/bootstrap
# Use returned api_key as X-Nimbusware-Api-Key on subsequent calls
```

Buyer checklist: [enterprise-buyer.md](enterprise-buyer.md). Edition details: [product/editions.md](product/editions.md).
