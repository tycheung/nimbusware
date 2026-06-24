#!/usr/bin/env bash
# Mirror the default CI unit job locally (see .github/workflows/ci.yml).
# Optional: --with-integration (Postgres integration pytest), --with-e2e (pytest tests/e2e -m e2e).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export NIMBUSWARE_SKIP_PREFLIGHT="${NIMBUSWARE_SKIP_PREFLIGHT:-1}"
COV_JSON="${ROOT}/.ci_coverage.json"
SKIP_WEB=0
WITH_INTEGRATION=0
WITH_E2E=0
for arg in "$@"; do
  case "$arg" in
    --skip-web|-SkipWeb) SKIP_WEB=1 ;;
    --with-integration|-WithIntegration) WITH_INTEGRATION=1 ;;
    --with-e2e|-WithE2e) WITH_E2E=1 ;;
  esac
done

poetry run python scripts/faiss/rebuild_bundle_faiss_if_stale.py --dry-run
poetry run ruff check packages tests
poetry run python scripts/ci/audit_operator_env.py
poetry run python scripts/ci/run_openapi_ts_ci_gate.py
poetry run ruff format --check packages tests
poetry run python scripts/ci/run_prune_comments_ci_gate.py
poetry run python scripts/ci/run_explainer_export_lint_gate.py
poetry run python scripts/ci/run_workflow_explainer_init_ci_gate.py
poetry run python scripts/ci/run_loc_budget_ci_gate.py
mapfile -t _mypy_targets < <(poetry run python scripts/ci/mypy_ci_targets.py)
poetry run mypy "${_mypy_targets[@]}"
poetry run bandit -c pyproject.toml -r packages -lll -q
poetry run pip-audit
poetry run pytest tests -q -m "not integration and not slow and not benchmark" \
  --cov=packages \
  --cov-report=term-missing:skip-covered \
  --cov-report="json:${COV_JSON}" \
  --cov-fail-under=75
poetry run python scripts/ci/coverage_package_floors.py --report "${COV_JSON}"
rm -f "${COV_JSON}"

poetry run pytest tests/e2e/journeys/test_slice_e2e_workflow.py::test_micro_slice_web_apply_emits_slice_e2e_stage -q
poetry run python scripts/ci/run_framework_pack_ci_gate.py
poetry run python scripts/ci/run_bootstrap_ci_gate.py
poetry run python scripts/ci/run_publish_bootstrap_ci_gate.py
poetry run python scripts/ci/run_publish_launcher_ci_gate.py
poetry run python scripts/ci/run_playwright_button_ci_gate.py
poetry run python scripts/ci/run_publish_vscode_ci_gate.py
poetry run python scripts/ci/run_intent_to_patch_ci_gate.py
poetry run python scripts/ci/run_classifier_acceptance_ci_gate.py
poetry run python scripts/ci/run_llm_resolver_ci_gate.py
poetry run python scripts/ci/run_first_publish_ci_gate.py

if [[ "${SKIP_WEB}" -eq 0 ]] && command -v node >/dev/null 2>&1; then
  if [[ -f packages/nimbusware_maker_web/package.json ]]; then
    (cd packages/nimbusware_maker_web && npm ci --silent && npm test --silent)
  fi
  if [[ -f packages/nimbusware_admin_ui/package.json ]]; then
    NIMBUSWARE_OPENAPI_TS_REQUIRE_FULL=1 poetry run python scripts/codegen/openapi_to_ts.py
    (cd packages/nimbusware_admin_ui && npm ci --silent && npm run build --silent && npm test --silent)
  fi
  if [[ -f extensions/nimbusware-status/package.json ]]; then
    (cd extensions/nimbusware-status && npm ci --silent && npm run compile --silent)
  fi
  if [[ -f tests/e2e/web/package.json ]] && command -v npx >/dev/null 2>&1; then
    (cd tests/e2e/web && npm ci --silent && npx playwright install chromium && npm test --silent)
  fi
fi

if [[ "${WITH_INTEGRATION}" -eq 1 || "${WITH_E2E}" -eq 1 ]]; then
  if [[ -z "${NIMBUSWARE_DATABASE_URL:-}" ]]; then
    echo "NIMBUSWARE_DATABASE_URL is required when using --with-integration or --with-e2e" >&2
    exit 1
  fi
  export NIMBUSWARE_REPO_ROOT="${NIMBUSWARE_REPO_ROOT:-$ROOT}"
fi

if [[ "${WITH_INTEGRATION}" -eq 1 ]]; then
  bash "${ROOT}/scripts/ci/run_integration_like_ci.sh"
fi

if [[ "${WITH_E2E}" -eq 1 ]]; then
  export NIMBUSWARE_E2E_FLAKE_RETRIES=1
  poetry run pytest tests/e2e -q -m e2e --reruns 1 --reruns-delay 2
fi
