# Contributing

## Setup

```bash
poetry install
# Optional: poetry install --with faiss
#           poetry install --with redis
# Pyright langserver (slice LSP) is included in the default dev install.
cp .env.example .env
```

Python **>=3.10** (3.11+ recommended). See [README.md](README.md) for install and quick start.

## CI parity

Before opening a PR, run the full unit CI job locally:

```powershell
.\scripts\ci_check.ps1
```

```bash
./scripts/ci_check.sh
```

This runs: ruff check, [`scripts/audit_operator_env.py`](scripts/audit_operator_env.py), format check, mypy (targets from [`scripts/mypy_ci_targets.py`](scripts/mypy_ci_targets.py)), bandit, pip-audit, pytest with **75%** coverage floor and per-package floors for core libs, Maker/Admin vitest when `node` is available, and Playwright smoke in [`tests/e2e/web`](tests/e2e/web) when `package-lock.json` is present. On Linux/macOS, pass `--skip-web` to `ci_check.sh` to skip the optional Node block.

Optional Postgres jobs (slower; require `NIMBUSWARE_DATABASE_URL`):

```powershell
.\scripts\ci_check.ps1 -WithIntegration -WithE2e
```

```bash
./scripts/ci_check.sh --with-integration --with-e2e
```

GitHub PR CI mirrors unit + web via parallel jobs in [`.github/workflows/ci.yml`](.github/workflows/ci.yml); integration and e2e run as separate PR jobs. `tests/unit/test_ci_check_parity.py` guards script drift.

Standalone integration (same as `-WithIntegration`):

```bash
./scripts/run_integration_like_ci.sh
```

See [tests/README.md](tests/README.md) for test layout and markers.

**Browser verify (`slice.e2e`)** is opt-in for operators: enable `slice.e2e.enabled` in the micro_slice workflow and install Playwright locally, or set `NIMBUSWARE_SLICE_E2E_COMMAND`. PR unit CI runs [`tests/e2e/journeys/test_slice_e2e_workflow.py`](tests/e2e/journeys/test_slice_e2e_workflow.py) with a stub command; [`tests/unit/test_slice_e2e.py`](tests/unit/test_slice_e2e.py) covers the orchestrator hook without browsers.

## Code conventions

### Import boundaries

Architecture is enforced by [`tests/unit/test_import_graph.py`](tests/unit/test_import_graph.py):

- `nimbusware_orchestrator` must not import `nimbusware_api` at module level
- `nimbusware_extensions` must not import `nimbusware_orchestrator` at module level
- Web UIs call `/v1` via `fetch` or `nimbusware_client`; Python `services/*` remain the server-side pattern — not ad-hoc `httpx` in display helpers

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full layering map and [nomenclature](ARCHITECTURE.md#nomenclature) (**Nimbusware** = this repo; **Nimbusware** = online agentic system).

Do not use “Nimbusware” to mean the Nimbusware platform, API, Maker, or Admin Console.

### Linting

- **Do not** run repo-wide `ruff check --fix` — it strips intentional re-export imports in console facades.
- Formatting is enforced: `poetry run ruff format --check packages tests`

### Typing

Global mypy strict mode is configured in `pyproject.toml`. CI checks explicit tranches (B–E) via `mypy_ci_targets.py`. All `nimbusware_orchestrator._pipeline` modules are strict-checked islands (including `dev_factory`); there is no blanket `_pipeline.*` ignore.

Docker agent sandbox (`NIMBUSWARE_SANDBOX_BACKEND=docker`) requires a local Docker CLI; it is the Individual v1 container backend (multi-tenant VM sandboxes are deferred).

### Module size

Console `.py` files must stay **≤400 lines** ([`tests/unit/test_console_module_size.py`](tests/unit/test_console_module_size.py)).

## Security

See [SECURITY.md](SECURITY.md) for secret handling and production checklist.

## Documentation

- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md) (canonical); [docs/architecture.md](docs/architecture.md) is the ADR index only
- Doc index: [docs/README.md](docs/README.md)
- Package READMEs: `packages/*/README.md`
- ADRs: `docs/adr/`
- Deploy: `docs/deploy/`
- Optional docstring hygiene: `poetry run python scripts/trim_redundant_docstrings.py` on `packages/`, `tests/`, `scripts/` (review diff before commit)
- Security CI gates: [docs/security-quality-gates.md](docs/security-quality-gates.md)
- Enterprise buyer checklist: [docs/enterprise-buyer.md](docs/enterprise-buyer.md)
