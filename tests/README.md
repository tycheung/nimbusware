# Test layout

Pytest discovers tests under `tests/` with `pythonpath = ["packages"]` (see root `pyproject.toml`).

| Directory | Purpose |
|-----------|---------|
| `tests/unit/` | Default CI bulk — pure helpers, contracts, env wiring |
| `tests/api/` | FastAPI route and OpenAPI tests |
| `tests/console/` | Admin console display / explainer behavior |
| `tests/orchestrator/` | `RunOrchestrator` integration paths |
| `tests/integration/` | Postgres-marked (`-m integration`) |
| `tests/e2e/` | PR e2e subset (`-m e2e`); weekly operator smoke stays in `e2e_smoke.yml` |
| `tests/web/` | Web UI parity matrix (`@pytest.mark.web`) |
| `tests/e2e/web/` | Playwright smoke (PR `ci.yml` **web** job; path-filtered `web-tests.yml` on UI-only diffs) |
| `tests/fixtures/research/`, `tests/fixtures/stitch/` | Golden research/stitch data (enable with `HERMES_RESEARCH=1`, `HERMES_STITCH=1`) |
| `tests/benchmark/` | `pytest-benchmark` fleet preflight |
| `tests/fixtures/swe_bench/` | SWE-bench harness fixture; scored run via `scripts/swe_bench_harness.py --run --json` (see `tests/unit/test_swe_bench_harness.py`) |

## Conventions

- Add new tests under the themed folder above, not at the `tests/` root (enforced by `tests/unit/test_test_layout.py`).
- Mark slow suites with `@pytest.mark.slow`; integration with `@pytest.mark.integration`.
- Prefer importing shared constants (e.g. `DEFAULT_NIMBUSWARE_ADMIN_TOKEN`) from `nimbusware_env.admin_token` instead of hardcoding dev token strings.

## Postgres adapter coverage

`packages/hermes_store/postgres.py` is **omitted from the unit-test coverage denominator** (`pyproject.toml` `[tool.coverage.run] omit`). It is exercised only via `@pytest.mark.integration` tests (for example `tests/integration/test_event_store_postgres_integration.py`, config/IAM/projection integration modules). Do not add unit tests that mock Postgres solely to inflate coverage on that module; extend integration tests when changing the adapter.

## CI subsets

- **Local / PR parity:** `scripts/ci_check.ps1` or `ci_check.sh` — `ruff check`, `audit_operator_env.py`, `ruff format --check`, mypy (`scripts/mypy_ci_targets.py`: tranches B–E, UI packages under narrowed ignores, API pilot), bandit (`pyproject.toml` config), `pip-audit`, package coverage floors, pytest @ 75%; optional vitest + Playwright when Node is installed (`ci_check.sh --skip-web` to omit).
- **Default PR / GitHub unit job:** same pytest subset with `--cov-fail-under=75` (see `.github/workflows/ci.yml` **unit** job).
- **PR web job:** vitest (`nimbusware_maker_web`, `nimbusware_admin_ui`) + Playwright `tests/e2e/web` (parallel to unit; guarded by `tests/unit/test_ci_check_parity.py`).
- Coverage omits desktop launcher modules, `*_cli.py` entrypoints, console display/explainer modules, and `hermes_store/postgres.py` (Postgres adapter — covered by `tests/integration/`); library code including `*/services/**` stays in the denominator.
- **Per-package floors** (`scripts/coverage_package_floors.py`, ≥85%): `agent_core`, `hermes_store`, `hermes_executor`, `nimbusware_config`, `nimbusware_projections`. Global floor remains 75% on all non-omitted `packages/**` code.
- **Slow tests:** Orchestrator-heavy API cases use `@pytest.mark.slow` per test; core run create/list/idempotency (`tests/api/test_api_runs.py`) and Maker flows (`tests/api/test_maker_approval_api.py`, `tests/api/test_projects_api.py`) run on every PR.
- **Integration job:** `-m integration` (event append, config documents, IAM, projections).
- **E2E job (PR):** `pytest tests/e2e -q -m e2e` with Postgres (import smoke + API `run.created` timeline). Local opt-in: `ci_check.ps1 -WithE2e` or `ci_check.sh --with-e2e` after exporting `NIMBUSWARE_DATABASE_URL`.
- **Local integration opt-in:** `ci_check.ps1 -WithIntegration` or `ci_check.sh --with-integration` (delegates to `run_integration_like_ci.*`; requires Postgres).
- **Weekly slow:** `-m slow`.
- **SSH hardware (optional):** `.github/workflows/ssh_hardware_probe.yml` — weekly schedule + `workflow_dispatch`; fleet matrix via `NIMBUSWARE_HW_FLEET_HOSTS` ([`docs/deploy/ssh-hardware-probe.md`](../docs/deploy/ssh-hardware-probe.md)); PR unit CI uses `NIMBUSWARE_HW_SSH_MOCK=1`.

## UI coverage policy (Lane V2)

- Console display/explainer modules stay **out** of the coverage denominator (characterization + integration tests).
- All HTTP for panels must go through `packages/*/services/` (guarded by `test_no_streamlit_imports.py` and import-graph rules); service modules **are** in the denominator.
- Retired Streamlit `ui/` trees must not return (`test_ui_no_direct_http.py`).
- Production orchestrator modules must not use the `test_*.py` naming pattern reserved for pytest — see `test_writer_role_critique.py`.

## UI guards

- `tests/unit/test_console_page_imports.py` — import smoke for console service modules.
- `tests/unit/test_maker_app_imports.py` — Maker package import smoke.
