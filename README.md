# Nimbusware

**Local-first** platform for agentic software workflows: Maker + Admin web apps, a FastAPI control plane, and an event-sourced runtime with tests, security gates, and optional local LLMs.

Capability calls (chat, sandbox, memory, …) go through **[SwissArmyNoife](../SwissArmyNoife)** — Nimbusware keeps product orchestration. See [product overview](docs/product/overview.md).

| | |
|--|--|
| **Version** | `0.5.0` |
| **Python** | `>=3.10` (3.11+ recommended) |
| **License** | [GPL-3.0](LICENSE) |

## Quick start

```bash
poetry install
python scripts/install_nimbusware.py --skip-postgres   # or full install with Postgres
poetry run nimbusware-run --quick                      # in-memory demo, no DB
```

Open Maker at [http://127.0.0.1:8000/v1/maker/app/](http://127.0.0.1:8000/v1/maker/app/).

- Full install & run options: **[docs/getting-started.md](docs/getting-started.md)**
- Desktop launcher: **[docs/deploy/launcher.md](docs/deploy/launcher.md)**
- Who is this for? **[docs/product/overview.md](docs/product/overview.md)** (individuals, enterprise, personas)

Optional `.env` presets: `NIMBUSWARE_OPERATOR_PRESET=offline`, `local-llm`, or `production`.

## Documentation

Everything lives under **[docs/README.md](docs/README.md)**. Common entry points:

| I want to… | Start here |
|------------|------------|
| Install and run | [docs/getting-started.md](docs/getting-started.md) |
| Use Maker | [docs/product/maker.md](docs/product/maker.md) |
| First full-stack app | [docs/product/journeys/README.md](docs/product/journeys/README.md) |
| Admin / fleet | [docs/product/admin.md](docs/product/admin.md) |
| Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Contribute / CI | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security | [SECURITY.md](SECURITY.md) |

## Architecture at a glance

```text
Maker / Admin UI  →  api (/v1)  →  orchestrator  →  event store (Postgres)
                              ↓                      ↓
                       projections            config + memory
```

Package map and import rules: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## SwissArmyNoife

Installer and desktop launcher **clone/update** SwissArmyNoife beside Nimbusware (`../SwissArmyNoife` by default) and optionally `cargo build` MCP + HTTP admin. They also set `NIMBUSWARE_BROKER_HTTP` when unset.

Nimbusware talks to the broker via `packages/broker_client/` (dual-run / peel). Flags: Agentic [docs/dual-run-flags.md](../docs/dual-run-flags.md) · MCP roles: [docs/mcp-split.md](../docs/mcp-split.md) · broker MCP setup: [SwissArmyNoife/docs/mcp-setup.md](../SwissArmyNoife/docs/mcp-setup.md).

```bash
# After install — start HTTP admin for peel (port 8787):
cd ../SwissArmyNoife && cargo run -p http-admin
```

Maker/IDE MCP (`packages/mcp`) is **separate** from SwissArmyNoife capability MCP — register both when you need both.

## Repository layout

```
packages/     Python libraries (orchestrator, api, maker, store, …)
configs/      Workflows, personas, bundles, templates
docs/         Operator and developer documentation
scripts/      Install, CI, runbooks
tests/        Pytest suite
```

## CLI essentials

```bash
poetry run nimbusware-run          # Desktop: API + Maker
poetry run nimbusware-admin        # Desktop: API + Admin
poetry run nimbusware-launcher     # Install / update GUI
poetry run nimbusware-api          # API only
poetry run nimbusware-mcp          # Maker/IDE MCP bridge (stdio)
```

Full list: [docs/reference/cli.md](docs/reference/cli.md).

## Contributing

```bash
./scripts/ci/ci_check.sh    # Linux/macOS
.\scripts\ci\ci_check.ps1   # Windows
```

Details (test counts, stream matrix, LOC budget, comment prune): **[CONTRIBUTING.md](CONTRIBUTING.md)**.

