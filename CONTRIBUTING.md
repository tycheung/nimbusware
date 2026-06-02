# Contributing

## Setup

```bash
poetry install
# Optional: poetry install --with faiss
#           poetry install --with redis
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

This runs: ruff check + format, mypy (targets from [`scripts/mypy_ci_targets.py`](scripts/mypy_ci_targets.py)), bandit, pip-audit, pytest with **75%** coverage floor and per-package floors for core libs.

Integration tests (Postgres required):

```bash
./scripts/run_integration_like_ci.sh
```

See [tests/README.md](tests/README.md) for test layout and markers.

## Code conventions

### Import boundaries

Architecture is enforced by [`tests/unit/test_import_graph.py`](tests/unit/test_import_graph.py):

- `hermes_orchestrator` must not import `nimbusware_api` at module level
- `hermes_extensions` must not import `hermes_orchestrator` at module level
- Streamlit UI must use `services/*` and `nimbusware_client` — not direct `httpx`

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full layering map and [nomenclature](ARCHITECTURE.md#nomenclature) (**Nimbusware** = this repo; **Hermes** = online agentic system).

Do not use “Hermes” to mean the Nimbusware platform, API, Maker, or Admin Console.

### Linting

- **Do not** run repo-wide `ruff check --fix` — it strips intentional re-export imports in console facades.
- Formatting is enforced: `poetry run ruff format --check packages tests`

### Typing

Global mypy strict mode is configured in `pyproject.toml`. CI checks explicit tranches (B–E) via `mypy_ci_targets.py`. Pipeline mixins under `hermes_orchestrator._pipeline.*` remain ignored until typed incrementally.

### Module size

Console `.py` files must stay **≤400 lines** ([`tests/unit/test_console_module_size.py`](tests/unit/test_console_module_size.py)).

## Security

See [SECURITY.md](SECURITY.md) for secret handling and production checklist.

## Documentation

- Package-level READMEs live under `packages/*/README.md`
- ADRs under `docs/adr/`
- Deploy reference under `docs/deploy/`
