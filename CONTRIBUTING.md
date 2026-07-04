# Contributing

## Setup

```bash
poetry install
# Optional: poetry install --with faiss
#           poetry install --with redis
# Pyright langserver (slice LSP) is included in the default dev install.
cp .env.example .env
```

Python **>=3.10** (3.11+ recommended). See [docs/getting-started.md](docs/getting-started.md) for install and quick start.

## CI parity

Before opening a PR, run the full unit CI job locally:

```powershell
.\scripts\ci_check.ps1
```

```bash
./scripts/ci/ci_check.sh
```

This runs: ruff check, [`scripts/ci/audit_operator_env.py`](scripts/ci/audit_operator_env.py), [`scripts/ci/run_openapi_ts_ci_gate.py`](scripts/ci/run_openapi_ts_ci_gate.py), format check, **prune-comments gate** (`run_prune_comments_ci_gate.py`), **explainer-export lint** (`run_explainer_export_lint_gate.py`), **LOC budget** (`run_loc_budget_ci_gate.py`), mypy (targets from [`scripts/ci/mypy_ci_targets.py`](scripts/ci/mypy_ci_targets.py)), bandit, pip-audit, pytest with **75%** coverage floor and per-package floors for core libs, Maker/Admin vitest when `node` is available (`npm run build` for Admin UI before vitest/Playwright), the `slice.e2e` apply journey gate, and **106** Playwright tests across **60** spec files in [`tests/e2e/web`](tests/e2e/web) when `package-lock.json` is present. On Linux/macOS, pass `--skip-web` to `ci_check.sh` to skip the optional Node block.

Optional Postgres jobs (slower; require `NIMBUSWARE_DATABASE_URL`):

```powershell
.\scripts\ci_check.ps1 -WithIntegration -WithE2e
```

```bash
./scripts/ci/ci_check.sh --with-integration --with-e2e
```

GitHub PR CI mirrors unit + web via parallel jobs in [`.github/workflows/ci.yml`](.github/workflows/ci.yml); integration and e2e run as separate PR jobs. `tests/unit/test_ci_check_parity.py` guards script drift.

Standalone integration (same as `-WithIntegration`):

```bash
./scripts/ci/run_integration_like_ci.sh
```

See [tests/README.md](tests/README.md) for test layout and markers.

**Fast gates** (subset before full CI): `poetry run python scripts/ci/fast_gates.py` — ruff, workflow YAML, LOC budget, module size, import boundary, stage registry, workflow registry, and complexity gates.

**Operator presets:** set `NIMBUSWARE_OPERATOR_PRESET` to `offline`, `local-llm`, or `production` in `.env` to apply transport defaults at startup (`packages/env/operator_presets.py`).

**Context efficiency:** cache-aware prompts thread `cache_blocks` through `ModelBindingResolver`; token usage persists as rate-limited `context.budget.sampled` events; Maker Progress SSE uses tail fetch + `progress_delta` merge; memory index rebuild skips unchanged event fingerprints; campaign artifact bundle at `GET /v1/runs/{id}/campaign-artifact-bundle`. See [ARCHITECTURE.md](../ARCHITECTURE.md#context-efficiency-jul-2026).

**Composite contract tests:** multi-case API/helper contracts belong in `tests/unit/composite_contracts/*_matrix.py` with parametrized runners (`matrix_runner.py`); keep per-file tests under ~150 lines.

**Browser verify (`slice.e2e`)** is **on by default** in [`configs/workflows/micro_slice.yaml`](configs/workflows/micro_slice.yaml). Install Playwright locally or set `NIMBUSWARE_SLICE_E2E_COMMAND`; the stage **SKIP**s when no runner is available. PR unit CI runs [`tests/e2e/journeys/test_slice_e2e_workflow.py`](tests/e2e/journeys/test_slice_e2e_workflow.py) with a command that asserts `index.html` exists in the fixture workspace; [`tests/unit/test_slice_e2e.py`](tests/unit/test_slice_e2e.py) covers the orchestrator hook without browsers.

PR **e2e** job (Postgres) retries flaky journeys once: `pytest tests/e2e -m e2e --reruns 1` via `pytest-rerunfailures` (`NIMBUSWARE_E2E_FLAKE_RETRIES=1`). Weekly [`.github/workflows/e2e_flake_monitor.yml`](.github/workflows/e2e_flake_monitor.yml) runs the same suite on a schedule and opens an issue when it fails. Local: `ci_check.ps1 -WithE2e` mirrors the same flags.

## Code conventions

### Import boundaries

Architecture is enforced by [`tests/unit/test_import_graph.py`](tests/unit/test_import_graph.py):

- `orchestrator` must not import `api` at module level
- Console/API/maker/projections must not import workflow block modules directly (use `orchestrator.workflow.registry`)
- `extensions` must not import `orchestrator` at module level
- Web UIs call `/v1` via `fetch` or `client`; Python `services/*` remain the server-side pattern — not ad-hoc `httpx` in display helpers

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full layering map and [nomenclature](ARCHITECTURE.md#nomenclature) (**Nimbusware** = this repository and product). Use **agent runtime** or **run pipeline** when you need to name the orchestration layer without repeating the product name.

### Linting

- **Do not** run repo-wide `ruff check --fix` — it strips intentional re-export imports in console facades.
- Formatting is enforced: `poetry run ruff format --check packages tests`

### Typing

Global mypy strict mode is configured in `pyproject.toml`. CI checks explicit tranches (B–E) via `mypy_ci_targets.py` and currently passes with **0** errors. All `orchestrator._pipeline` modules are strict-checked islands (including `dev_factory`); there is no blanket `_pipeline.*` ignore.

Docker agent sandbox (`NIMBUSWARE_SANDBOX_BACKEND=docker`) requires a local Docker CLI; it is the Individual v1 container backend (multi-tenant VM sandboxes are deferred).

### Module size

Console and all `packages/**/*.py` modules must stay **≤1000 lines** ([`tests/unit/test_package_module_size.py`](tests/unit/test_package_module_size.py)). Prefer cohesive modules over file-count splitting. Maker web tabs use thin `*.js` shells plus `*_ui.js` helpers — see [ARCHITECTURE.md](ARCHITECTURE.md).

### LOC budget

`packages/` Python non-blank lines are capped by [`scripts/ci/run_loc_budget_ci_gate.py`](scripts/ci/run_loc_budget_ci_gate.py) (baseline in [`scripts/ci/loc_baseline.json`](scripts/ci/loc_baseline.json)). Prefer net LOC reduction when refactoring; update the baseline only when growth is intentional and justified in the PR.

## Security

See [SECURITY.md](SECURITY.md) for secret handling and production checklist.

## Documentation

- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md) (canonical); [docs/architecture.md](docs/architecture.md) is the ADR index only
- **Package catalog:** [packages/README.md](packages/README.md) (all `packages/*` responsibilities); per-package detail in `packages/*/README.md`
- ADRs: `docs/adr/`
- Deploy: `docs/deploy/` (integrator external CI: [external-ci-bridge.md](docs/deploy/external-ci-bridge.md))
- Optional docstring hygiene: `poetry run python scripts/ci/trim_redundant_docstrings.py` and `scripts/ci/prune_verbose_comments.py` (CI enforces prune gate; review diff before bulk local runs)
- Console display metrics: prefer YAML specs under `configs/displays/` or `configs/explainers/` wired through `install_workflow_metrics_from_spec` (e.g. `run_escalated_{latest,history,delta}.yaml`); use `explainer_core.build_operator_metrics` + `install_operator_metrics_module` for bespoke cases only
- Greenfield scaffolds: `configs/factory/` (minimal frontend index) and `configs/templates/` (Safe Coding smoke pytest/Playwright stubs)
- Explainer captions: use `explainer_core.field_caption` helpers and `env_captions.ENV_*_TEMPLATES` registry lookups instead of duplicating load-error / int guards
- Maker operator ribbons live under `packages/maker_web/static/js/*-ribbon.js` and `ribbon-shared.js`
- Security CI gates: [docs/security-quality-gates.md](docs/security-quality-gates.md)
- Enterprise buyer checklist: [docs/enterprise-buyer.md](docs/enterprise-buyer.md)
