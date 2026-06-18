# Test layout

Pytest discovers **3,684** items under `tests/` with `pythonpath = ["packages", "tests"]` (see root `pyproject.toml`). The PR **unit** CI subset runs **~2,824** tests at **≥75%** coverage (82% total line coverage as of Jun 2026). Fixture repos under `tests/fixtures/repos/` are excluded from collection (`norecursedirs`). Playwright specs use a **120s** timeout (`tests/e2e/web/playwright.config.ts`) so campaign/API flows stay stable under CI parallel workers.

| Directory | Purpose |
|-----------|---------|
| `tests/unit/` | Default CI bulk — pure helpers, contracts, env wiring (incl. `test_install_happy_path.py`) |
| `tests/api/` | FastAPI route and OpenAPI tests |
| `tests/console/` | Admin console display / explainer behavior |
| `tests/orchestrator/` | `RunOrchestrator` integration paths |
| `tests/integration/` | Postgres-marked (`-m integration`); includes `test_campaign_multi_tick.py` |
| `tests/e2e/` | PR e2e subset (`-m e2e`); L1 journeys in `tests/e2e/journeys/` (`e2e_journey`); stack tests (`e2e_stack`) |
| `tests/e2e/harness/` | Shared journey helpers (`JourneyClient`, golden timelines, stack subprocess, embed/in-process dispatch worker) |
| `tests/e2e/journeys/` | Operator micro-slice, lifecycle, external workspace, enterprise auth, launch-eval replay (+ dev-env merge), campaign dispatch worker, slice.e2e apply, interjection queue ordering, stack soak, factory cadence, PUT E2E CI gate, fullstack launch, unknown-SPA + write-replan launch-test journeys, framework detect + PUT-preview SPA packs, live theater SSE stack journey, golden timeline profiles (web/fullstack/factory), `tiny_api_app` micro-slice + campaign dispatch; API chat mid-thread patch→slice (`test_chat_mid_thread_patch_to_slice_journey`) |
| `tests/integration/` | Postgres, Redis dispatch worker stack (`test_redis_dispatch_worker_stack.py`, `-m integration`) |
| `tests/e2e/golden/timelines/` | Minimum timeline subsequences (`micro_slice_web_apply.json`, `micro_slice_fullstack_created.json`, `campaign_factory_zero_touch_created.json`, etc.) |
| `tests/fixtures/repos/` | Attachable workspace copies (`tiny_python_app`, `tiny_web_app`, `tiny_broken_app`, `tiny_api_app`, `tiny_go_app`, `tiny_jvm_app`, `orphan_trap`, `fastapi_routes`) |
| `tests/fixtures/campaign/` | Golden multi-tick campaign timeline for integration tests |
| `tests/fixtures/launch_eval/` | Golden scorecard floors + campaign replay manifest (`golden_replay_manifest.json`, CRM + todo_api + contacts_api snapshots) |
| `tests/fixtures/factory/` | Factory golden replay manifest (`golden_factory_replay_manifest.json` — crm, contacts, todo, static_site T1/T3) + legacy `golden_factory_replay.json` |
| `tests/web/` | Web UI parity matrix (`@pytest.mark.web`) + launch wiring (`parity_launch_wiring.yaml`) + chat wiring (`parity_chat_wiring.yaml`; **≥80%** Chat-related `web: true` rows) + admin wiring (`parity_admin_wiring.yaml`) + IDE MCP wiring (`parity_ide_wiring.yaml`) + chat journey scenarios (`chat_journey_scenarios.yaml`; **≥80%** congruent-thread journeys) |
| `tests/e2e/web/` | Playwright smoke, Chat patch/override/branch/escalation/theater, Admin operator chat classifier cards, Admin hardware catalog strip, Admin fleet hardware table + rescan, Admin run-detail panels + audit export, Admin config/fleet/nav smoke, Admin critic packs config tab, home intents + factory hero demos, Progress gate-fail action cards, Chat autopilot ladder hint, Settings hybrid routing presets, apply-slice, session hub, launch scorecard (dimension rows + dev-env merge), Settings launch check + chat resume, scoped compaction toolbar, operator ribbons (incl. variant arena fitness + crossover merged), memory influence table, council ribbon gaps, variant fitness, campaign progress + full replay, mobile theater parity (**55** tests / **41** spec files; **4** workers, **1** retry, **120s** timeout; sets `NIMBUSWARE_API_BASE` to test server port). Parity matrix rows: readiness CTAs, Review open-PR CTA, Progress gate_summary, memory influence + council + variant (`parity_progress_wiring.yaml`), IDE MCP classify/patch/interject/fork, hybrid routing API (`test_routing_presets_api.py`) |
| `tests/fixtures/research/`, `tests/fixtures/stitch/` | Golden research/stitch data (enable with `NIMBUSWARE_RESEARCH=1`, `NIMBUSWARE_STITCH=1`) |
| `tests/benchmark/` | `pytest-benchmark` fleet preflight |
| `tests/fixtures/swe_bench/` | Local micro_slice regression fixture (stub implement; not public SWE-bench); scored run via `scripts/benchmarks/swe_bench_harness.py --run --json` |

## Conventions

- Add new tests under the themed folder above, not at the `tests/` root (enforced by `tests/unit/test_test_layout.py`).
- Mark slow suites with `@pytest.mark.slow`; integration with `@pytest.mark.integration`.
- Prefer importing shared constants (e.g. `DEFAULT_NIMBUSWARE_ADMIN_TOKEN`) from `nimbusware_env.admin_token` instead of hardcoding dev token strings.

## Postgres adapter coverage

`packages/nimbusware_store/postgres.py` is **omitted from the unit-test coverage denominator** (`pyproject.toml` `[tool.coverage.run] omit`). It is exercised only via `@pytest.mark.integration` tests (for example `tests/integration/test_event_store_postgres_integration.py`, config/IAM/projection integration modules). Do not add unit tests that mock Postgres solely to inflate coverage on that module; extend integration tests when changing the adapter.

## CI subsets

- **Local / PR parity:** `scripts/ci/ci_check.ps1` or `ci_check.sh` — `ruff check`, `audit_operator_env.py`, `run_openapi_ts_ci_gate.py`, `ruff format --check`, mypy (`scripts/ci/mypy_ci_targets.py`: tranches B–E, UI packages under narrowed ignores, API pilot), bandit (`pyproject.toml` config), `pip-audit`, package coverage floors, framework-pack + intent-to-patch + classifier-acceptance SLO gates, pytest @ 75%, slice.e2e apply journey gate (`NIMBUSWARE_SLICE_E2E_COMMAND`); optional vitest, VS Code extension compile (`extensions/nimbusware-status`), and Playwright when Node is installed (`ci_check.sh --skip-web` to omit).
- **Default PR / GitHub unit job:** same pytest subset with `--cov-fail-under=75` (see `.github/workflows/ci.yml` **unit** job).
- **PR web job:** [`.github/workflows/web-tests.yml`](.github/workflows/web-tests.yml) — vitest + Playwright without Postgres (`NIMBUSWARE_DATABASE_URL=""`); Postgres-backed journeys stay in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) **e2e** job. Contract: `tests/web/test_web_workflow_env.py`.
- Coverage omits desktop launcher modules, `*_cli.py` entrypoints, console display/explainer modules, and `nimbusware_store/postgres.py` (Postgres adapter — covered by `tests/integration/`); library code including `*/services/**` stays in the denominator.
- **Per-package floors** (`scripts/ci/coverage_package_floors.py`, ≥85%): `agent_core`, `nimbusware_store`, `nimbusware_executor`, `nimbusware_config`, `nimbusware_projections`. Global floor remains 75% on all non-omitted `packages/**` code.
- **Slow tests:** Orchestrator-heavy API cases use `@pytest.mark.slow` per test; core run create/list/idempotency (`tests/api/test_api_runs.py`) and Maker flows (`tests/api/test_maker_approval_api.py`, `tests/api/test_projects_api.py`) run on every PR.
- **Integration job:** `-m integration` (event append, config documents, IAM, projections).
- **E2E job (PR):** `pytest tests/e2e -q -m e2e` with Postgres; `--reruns 1` flake budget via `pytest-rerunfailures` and `NIMBUSWARE_E2E_FLAKE_RETRIES`. Local: `pytest tests/e2e/journeys -m e2e_journey -q` (no Postgres required for TestClient journeys; includes chat patch timing, mid-thread patch→slice, launch-test static HTML / unknown SPA / all framework detect paths / write-replan with keyboard + optional mouse fidelity). Stack + Postgres: `test_chat_postgres_persistence_journey.py`, `test_theater_stream_journey.py` (`-m "e2e_stack and integration"`). API theater SSE: `tests/api/test_api_theater_stream.py`. Chat parity wiring gate: `tests/web/test_parity_chat_wiring.py` (≥80% of Chat-related `web: true` rows, incl. `theater_sse_live` and `deep_link_run_id`). Admin parity wiring gate: `tests/web/test_parity_admin_wiring.py`. Operator smoke: `scripts/ops/e2e_smoke.py --profile app` includes journey pytest. Local opt-in: `ci_check.ps1 -WithE2e` or `ci_check.sh --with-e2e` after exporting `NIMBUSWARE_DATABASE_URL`.
- **E2E flake monitor (weekly):** [`.github/workflows/e2e_flake_monitor.yml`](../.github/workflows/e2e_flake_monitor.yml) — Postgres e2e with `--reruns 1`; log artifact + `e2e-flake-failure` issue on failure.
- **Local integration opt-in:** `ci_check.ps1 -WithIntegration` or `ci_check.sh --with-integration` (delegates to `run_integration_like_ci.*`; requires Postgres).
- **Weekly slow:** [`.github/workflows/slow_tests.yml`](../.github/workflows/slow_tests.yml) — `-m slow`, **stack-soak**, **fullstack-weekly-soak** (`scripts/ops/run_fullstack_weekly_soak.py`), **dev-env-weekly-soak**, and **redis-fleet-soak** (dual Redis via `NIMBUSWARE_REDIS_FLEET_URLS`; see runbooks above).
- **Framework pack PR gate:** `scripts/ci/run_framework_pack_ci_gate.py` in default PR **unit** job (unit smoke + detect + PUT-preview for seven SPA packs + static HTML + write-replan + unknown-SPA journeys with keyboard/mouse fidelity; installs Chromium via `playwright` dev dependency).
- **Bootstrap wheel PR gate:** `scripts/ci/run_bootstrap_ci_gate.py` (wheel build + isolated `pip install --target` smoke + fresh-venv subprocess install).
- **Publish bootstrap workflow gate:** `scripts/ci/run_publish_bootstrap_ci_gate.py` (guards `.github/workflows/publish_bootstrap.yml` required TestPyPI/PyPI steps).
- **Publish VS Code extension workflow gate:** `scripts/ci/run_publish_vscode_ci_gate.py` (guards `.github/workflows/publish_vscode_extension.yml` required VSCE steps).
- **Redis fleet soak (ops):** [`scripts/runbooks/e2e_redis_fleet_soak_runbook.md`](../scripts/runbooks/e2e_redis_fleet_soak_runbook.md) — integration Redis dispatch stack (`test_redis_dispatch_worker_stack.py`, `-m integration`).
- **Launch eval (weekly):** `.github/workflows/launch_eval.yml` — `scripts/benchmarks/launch_eval.py --matrix` on catalog default workspaces; unit coverage in `tests/unit/test_launch_eval_attach_context.py`.
- **SSH hardware (optional):** `.github/workflows/ssh_hardware_probe.yml` — weekly schedule + `workflow_dispatch`; fleet matrix via `NIMBUSWARE_HW_FLEET_HOSTS` ([`docs/deploy/ssh-hardware-probe.md`](../docs/deploy/ssh-hardware-probe.md)); PR unit CI uses `NIMBUSWARE_HW_SSH_MOCK=1`.

## UI coverage policy (Lane V2)

- Console display/explainer modules stay **out** of the coverage denominator (characterization + integration tests).
- All HTTP for panels must go through `packages/*/services/` (guarded by `test_no_streamlit_imports.py` and import-graph rules); service modules **are** in the denominator.
- Retired Streamlit `ui/` trees must not return (`test_ui_no_direct_http.py`).
- Production orchestrator modules must not use the `test_*.py` naming pattern reserved for pytest — see `test_writer_role_critique.py`.

## UI guards

- `tests/unit/test_console_page_imports.py` — import smoke for console service modules.
- `tests/unit/test_maker_app_imports.py` — Maker package import smoke.
