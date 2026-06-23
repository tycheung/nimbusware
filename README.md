# Nimbusware

**Local-first** platform for adversarial agentic software workflows: a FastAPI control plane, **Maker** and **Admin** web apps, and an event-sourced agent runtime with unanimous gates, verifiers, and optional Ollama-backed LLM stages.

| | |
|--|--|
| **Version** | `0.5.0` |
| **Python** | `>=3.10` (3.11+ recommended) |
| **Default workflow** | `micro_slice` |
| **License** | [GPL-3.0](LICENSE) |

**Individuals** — build and fix software on your machine with an agent that must pass tests and security gates, not just generate code. Tune **autonomy** (when the operator is asked) and **enforcement depth** (how strictly workspaces are verified) independently. Campaign workflows decompose a `business_prompt` into verified micro-slices (heuristic or LLM backlog). Maker Chat supports per-role model swap, role claims, and an **Accessible compute** drawer for collaborative mesh sessions.  
**Enterprise** — self-hosted control plane for governed agentic development: audit every run, steer autonomy, standardize quality without a SaaS black box.

## Quick start

```bash
poetry install
python scripts/install_nimbusware.py --skip-postgres   # or full install with Postgres
poetry run nimbusware-run --quick                      # in-memory demo, no DB
```

Open Maker at `http://127.0.0.1:8000/v1/maker/app/`. Full install and run options: **[docs/getting-started.md](docs/getting-started.md)**.

### Desktop launcher (Windows / macOS / Linux)

Download the platform build from GitHub Releases (`launcher-v*` tags) or build with `scripts/publish/build_launcher.ps1` / `build_launcher.sh`. The launcher offers **Quick setup** (barebones) and **Full setup** (Postgres + Ollama). Details: **[docs/deploy/launcher.md](docs/deploy/launcher.md)**.

```bash
pip install nimbusware-bootstrap
nimbusware-bootstrap --print-only    # launcher URL + curl install lines
```

## Documentation

| I want to… | Start here |
|------------|------------|
| Install, bootstrap, and run | [docs/getting-started.md](docs/getting-started.md) |
| Use the Maker app | [docs/product/maker.md](docs/product/maker.md) |
| Understand refactor / code-intel | [docs/agent-runtime.md](docs/agent-runtime.md#refactor-stage) |
| Use the Admin Console | [docs/product/admin.md](docs/product/admin.md) |
| Understand editions & auth | [docs/product/editions.md](docs/product/editions.md) |
| Browse API endpoints | [docs/product/api-overview.md](docs/product/api-overview.md) |
| Understand the agent pipeline | [docs/agent-runtime.md](docs/agent-runtime.md) |
| Enforcement depth vs autopilot | [docs/adr/026-enforcement-depth-slider.md](docs/adr/026-enforcement-depth-slider.md) |
| Operator ribbons (Maker) | Progress + Chat: `interjection-ribbon.js`, `autopilot-ribbon.js`, `enforcement-ribbon.js`, `ribbon-shared.js`, `operator-default-profiles.js` |
| Read architecture & packages | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Configure settings (~141 catalog keys) | [docs/operator-settings.md](docs/operator-settings.md) |
| Deploy to production / K8s | [docs/deploy/README.md](docs/deploy/README.md) |
| First PyPI / VSCE publish | [docs/deploy/pypi-publish.md](docs/deploy/pypi-publish.md), `scripts/publish/first_publish_gates.py` |
| Desktop launcher releases | [docs/deploy/launcher.md](docs/deploy/launcher.md) |
| Run tests & CI locally | [CONTRIBUTING.md](CONTRIBUTING.md), [tests/README.md](tests/README.md) |
| Compute mesh & workers | [docs/compute-mesh.md](docs/compute-mesh.md) |
| Security & compliance | [SECURITY.md](SECURITY.md), [docs/enterprise-buyer.md](docs/enterprise-buyer.md) |
| **Full doc index** | **[docs/README.md](docs/README.md)** |

## Editions

| Edition | Install | Scope |
|---------|---------|--------|
| **Individual** (default) | `python scripts/install_nimbusware.py` | Single operator, repo-scoped memory |
| **Enterprise** | `… --edition enterprise` | IAM, fleet memory, Redis workers, fleet SLI |

Details: [docs/product/editions.md](docs/product/editions.md).

## Architecture at a glance

```text
Maker / Admin UI  →  nimbusware_api (/v1)  →  orchestrator  →  event store (Postgres)
                              ↓                      ↓
                       projections            config + memory
```

Package map, import rules, and CI: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## Repository layout

```
packages/     Python libraries (orchestrator, api, maker, store, …)
configs/      Workflow YAML, personas, bundles
docs/         Operator and developer documentation
scripts/      Install, CI, benchmarks, runbooks
tests/        Pytest suite (unit, api, integration, e2e)
```

## CLI essentials

```bash
poetry run nimbusware-run          # Desktop: API + Maker
poetry run nimbusware-admin        # Desktop: API + Admin
poetry run nimbusware-launcher     # Install / update GUI (or use release binary)
poetry run nimbusware-api          # API only
poetry run nimbusware-mcp          # IDE bridge (stdio MCP)
```

Full command list: [docs/reference/cli.md](docs/reference/cli.md).

## Contributing

```bash
./scripts/ci/ci_check.sh    # Linux/macOS (matches PR CI)
.\scripts\ci\ci_check.ps1   # Windows
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for import boundaries, linting, and typing tranches. Default CI runs **~3028** unit tests (plus 81 Playwright specs across 48 spec files); full pytest collection is **3873** tests. CI also enforces prune-comments, explainer-export lint, and packages LOC budget gates (`scripts/ci/run_*_ci_gate.py`; baseline **94,789** lines in `scripts/ci/loc_baseline.json`).
