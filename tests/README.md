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

- **Default PR / local CI:** `pytest tests -m "not integration and not slow and not benchmark"` with `--cov-fail-under=72` (see `scripts/ci_check.ps1`).
- Coverage omits Streamlit `pages/**`, Maker `ui/**`, desktop launcher modules, and `*_cli.py` entrypoints; library code including `*/services/**` stays in the denominator.
- Fast API/auth/OpenAPI tests live in `tests/api/` without the blanket `slow` marker; orchestrator-heavy API suites stay `@pytest.mark.slow`.
- Integration job: `-m integration`.
- Weekly slow: `-m slow`.

## UI coverage policy (Lane V2)

- Streamlit `pages/**` and Maker `ui/**` stay **out** of the coverage denominator until optional UI characterization tests land.
- All HTTP for panels must go through `packages/*/services/` (guarded by `test_ui_no_direct_http.py`); service modules **are** in the denominator.
- Production orchestrator modules must not use the `test_*.py` naming pattern reserved for pytest — see `test_writer_role_critique.py` (fo620).

## UI guards

- `tests/unit/test_console_page_imports.py` — import smoke for Streamlit section entrypoints.
- `tests/unit/test_maker_app_imports.py` — Maker package import smoke.
