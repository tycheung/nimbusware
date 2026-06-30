# Nimbusware

**Local-first** platform for adversarial agentic software workflows: a FastAPI control plane, **Maker** and **Admin** web apps, and an event-sourced agent runtime with unanimous gates, verifiers, and optional Ollama-backed LLM stages.

| | |
|--|--|
| **Version** | `0.5.0` |
| **Python** | `>=3.10` (3.11+ recommended) |
| **Default workflow** | `micro_slice` |
| **License** | [GPL-3.0](LICENSE) |

**Individuals** — build and fix software on your machine with an agent that must pass tests and security gates, not just generate code. Greenfield **Build an app** flows run scope discovery in Maker Chat (with **Explain** hints on each question), freeze a stack manifest from `configs/stacks/`, then deliver via the `campaign_fullstack` workflow (API + web surfaces, contract gate, launch test). Manifests that include a **`deploy`** surface bind `infra_writer` for Terraform/CI slices (`configs/roles.yaml`); binding preflight reports `surface_stage_map` including `deploy → infra_writer`. Slice handoff packets carry `surface_id`, `stack_id`, and contract refs across campaign ticks; stack catalog entries enforce per-surface diff budgets during implement/replan. **Safe Coding** archetype uses `safe_coding_campaign_fullstack` for the same journey with extra approval gates and industry critics. The **Plan** tab shows per-slice surface badges and highlights the active slice with refactor/architecture maintenance cadence; **Progress** shows surface-aware slice headlines (e.g. “Web UI slice 2 passed”) and includes a deploy cockpit (Terraform validate, approve/apply, smoke tests, rollback, dev/staging/prod environment selector, CI timeline stages); campaigns with a `deploy` surface require smoke pass before completion; Chat supports `@discipline` mention autocomplete with backend routing to the interjection queue on active runs, **solo hat quick-switch chips** in the composer (synced with Settings), `@web` / `@api` surface steers (`[steer:web]` in Progress), plus a plain-language manifest approval card. **Safe Coding** Settings load industry critic packs from `GET /v1/platform/industry-critic-packs` (repo `configs/critic_packs/`). External chat webhooks persist `last_run_id` per `session_id` and route `@frontend` / `@qa` messages to the interjection queue on active runs ([integrations-external-chat.md](docs/integrations-external-chat.md)). **Engineer workspace** collab adds discipline rosters, join onboarding with a discipline picker, per-user discipline profiles and versioned agent prompt overlays (Settings **My agent overlays** or `configs/collab/users/`), role-claim conflict handling in Chat, and `@` routing to the interjection queue on active runs. The optional **VS Code / Cursor extension** (`extensions/nimbusware-status`) mirrors scope manifest approval, `@` discipline routing preview, and deploy deep links alongside MCP ([docs/ide-bridge.md](docs/ide-bridge.md)). Tune **autonomy** (when the operator is asked) and **enforcement depth** (how strictly workspaces are verified) independently. Campaign workflows decompose a `business_prompt` into verified micro-slices (heuristic or LLM backlog with surface-aware routing). Maker Chat supports per-role model swap, role claims, an in-session **Session models** drawer (provider + connection per role), and **Accessible compute** for collaborative mesh sessions. The **Engineer workspace** archetype enables and **persists** collab without editing `.env`. **Safe Coding** offers a zero-terminal Home wizard (scaffold → pre-commit → Playwright bootstrap with status polling).  
**Enterprise** — self-hosted control plane for governed agentic development: audit every run, fleet compliance dashboard (gate pass rates, slice histogram), tenant audit policy with **legal-hold toggle** (blocks event-store purge), **collab guest policy** and **regulated stack allowlist** in Admin Fleet, fleet governance summary in Maker Home (allowed deploy targets, mandatory discovery fields, deploy approval chain, compliance summary widget), deploy credential scope audit (`.nimbusware/platform/deploy_audit.jsonl` + Review timeline API), steer autonomy, standardize quality without a SaaS black box.

**Mobile native** (React Native / Expo) is **deferred** — web-first Maker ships first; see [docs/product/mobile.md](docs/product/mobile.md). **Manager PWA** (`?manager=1`) provides read-only Progress/Review plus Scope manifest approval on phone.

## Consumer personas

| Persona | Setup bundle | First-run choice | Docs |
|---------|--------------|------------------|------|
| **Safe Coding** | `default` | Safe Coding in Maker archetype picker | [docs/product/safe-coding.md](docs/product/safe-coding.md), [journeys/safe-coding-first-app.md](docs/product/journeys/safe-coding-first-app.md) |
| **Engineer workspace** | `default` | Engineer workspace in Maker (persists collab via Settings or archetype preset) | [docs/product/maker.md](docs/product/maker.md), [docs/collaborative-chat.md](docs/collaborative-chat.md), [journeys/engineer-first-app.md](docs/product/journeys/engineer-first-app.md) |
| **Enterprise AI** | `enterprise` | (strict env applied at install) | [docs/enterprise-buyer.md](docs/enterprise-buyer.md), [journeys/enterprise-first-app.md](docs/product/journeys/enterprise-first-app.md) |

Install with `--setup-bundle default` or `--setup-bundle enterprise` (see [docs/install-profiles.md](docs/install-profiles.md)). The desktop launcher offers **Quick setup**, **Full setup** (default bundle), and **Enterprise setup**.

## Quick start

```bash
poetry install
python scripts/install_nimbusware.py --skip-postgres   # or full install with Postgres
poetry run nimbusware-run --quick                      # in-memory demo, no DB
```

Open Maker at `http://127.0.0.1:8000/v1/maker/app/`. Full install and run options: **[docs/getting-started.md](docs/getting-started.md)**.

### Desktop launcher (Windows / macOS / Linux)

Download the platform build from GitHub Releases (`launcher-v*` tags) or build with `scripts/publish/build_launcher.ps1` / `build_launcher.sh`. The launcher offers **Quick setup** (barebones), **Full setup** (Postgres + Ollama, default bundle), and **Enterprise setup** (strict env). Details: **[docs/deploy/launcher.md](docs/deploy/launcher.md)**.

```bash
pip install nimbusware-bootstrap
nimbusware-bootstrap --print-only    # launcher URL + curl install lines
```

## Documentation

| I want to… | Start here |
|------------|------------|
| Install, bootstrap, and run | [docs/getting-started.md](docs/getting-started.md) |
| Use the Maker app | [docs/product/maker.md](docs/product/maker.md) |
| First full-stack app (per persona) | [docs/product/journeys/README.md](docs/product/journeys/README.md) |
| Model Hub (API keys + desktop subscriptions) | [docs/model-hub.md](docs/model-hub.md) |
| Safe Coding persona | [docs/product/safe-coding.md](docs/product/safe-coding.md) |
| Install profiles & setup bundles | [docs/install-profiles.md](docs/install-profiles.md) |
| Understand refactor / code-intel | [docs/agent-runtime.md](docs/agent-runtime.md#refactor-stage) |
| Use the Admin Console | [docs/product/admin.md](docs/product/admin.md) |
| Understand editions & auth | [docs/product/editions.md](docs/product/editions.md) |
| Browse API endpoints | [docs/product/api-overview.md](docs/product/api-overview.md) |
| Understand the agent pipeline | [docs/agent-runtime.md](docs/agent-runtime.md) |
| Enforcement depth vs autopilot | [docs/adr/026-enforcement-depth-slider.md](docs/adr/026-enforcement-depth-slider.md) |
| Operator ribbons (Maker) | Progress + Chat: `interjection-ribbon.js`, `autopilot-ribbon.js`, `enforcement-ribbon.js`, `ribbon-shared.js`, `operator-default-profiles.js` |
| Read architecture & packages | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Configure settings (~256 catalog keys) | [docs/operator-settings.md](docs/operator-settings.md) |
| Collaborative chat & disciplines | [docs/collaborative-chat.md](docs/collaborative-chat.md) |
| IDE bridge (MCP + VS Code extension) | [docs/ide-bridge.md](docs/ide-bridge.md) |
| Deploy pipeline (Terraform / CI) | [docs/product/deploy.md](docs/product/deploy.md) |
| Mobile native (deferred) | [docs/product/mobile.md](docs/product/mobile.md) |
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

Default CI runs **~3270** unit tests under the default pytest marker (plus **101** Playwright tests); full collection is **~4000** tests. CI enforces prune-comments, explainer-export lint, workflow-explainer init sync, archetype-fit, gate-comprehension, and collab-LLM audit gates (`scripts/ci/run_*_ci_gate.py`; LOC budget **103,382** non-blank Python lines in `packages/` per `scripts/ci/loc_baseline.json`).
