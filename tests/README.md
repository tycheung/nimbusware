# Test layout

Pytest discovers tests under `tests/` with `pythonpath = ["packages"]` (see root `pyproject.toml`).

| Directory | Purpose |
|-----------|---------|
| `tests/unit/` | Default CI bulk — pure helpers, contracts, env wiring |
| `tests/api/` | FastAPI route and OpenAPI tests |
| `tests/console/` | Admin console display / explainer behavior |
| `tests/orchestrator/` | `RunOrchestrator` integration paths |
| `tests/integration/` | Postgres-marked (`-m integration`) |
| `tests/e2e/` | Operator smoke checks |
| `tests/benchmark/` | `pytest-benchmark` fleet preflight |

## Conventions

- Add new tests under the themed folder above, not at the `tests/` root (enforced by `tests/unit/test_test_layout.py`).
- Mark slow suites with `@pytest.mark.slow`; integration with `@pytest.mark.integration`.
- Prefer importing shared constants (e.g. `DEFAULT_NIMBUSWARE_ADMIN_TOKEN`) from `nimbusware_env.admin_token` instead of hardcoding dev token strings.

## CI subsets

- Default PR CI: `pytest tests -m "not integration and not slow and not benchmark"` with `--cov-fail-under=70`
- Coverage omits Streamlit pages, Maker UI, desktop launcher apps (`nimbusware_env/*_app.py`, `desktop_common.py`, `linux_desktop_deps.py`), and CLI entrypoints (`*_cli.py`, package `cli.py`) — exercised via console/e2e/manual smoke; core library code stays in the denominator (fo504 / fo510).
- Fast API/auth/OpenAPI tests live in `tests/api/` without the blanket `slow` marker; orchestrator-heavy API suites stay `@pytest.mark.slow`
- Integration job: `-m integration`
- Weekly slow: `-m slow`
