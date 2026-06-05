#!/usr/bin/env bash
# Mirror the default CI unit job locally (see .github/workflows/ci.yml).
# Optional: --with-integration (Postgres integration pytest), --with-e2e (pytest tests/e2e -m e2e).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
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

poetry run python scripts/rebuild_bundle_faiss_if_stale.py --dry-run
poetry run ruff check packages tests
poetry run python scripts/audit_operator_env.py
poetry run ruff format --check packages tests
mapfile -t _mypy_targets < <(poetry run python scripts/mypy_ci_targets.py)
poetry run mypy "${_mypy_targets[@]}"
poetry run bandit -c pyproject.toml -r packages -lll -q
poetry run pip-audit
poetry run pytest tests -q -m "not integration and not slow and not benchmark" \
  --cov=packages \
  --cov-report=term-missing:skip-covered \
  --cov-report="json:${COV_JSON}" \
  --cov-fail-under=75
poetry run python scripts/coverage_package_floors.py --report "${COV_JSON}"
rm -f "${COV_JSON}"

if [[ "${SKIP_WEB}" -eq 0 ]] && command -v node >/dev/null 2>&1; then
  if [[ -f packages/nimbusware_maker_web/package.json ]]; then
    (cd packages/nimbusware_maker_web && npm ci --silent && npm test --silent)
  fi
  if [[ -f packages/nimbusware_admin_ui/package.json && -f packages/nimbusware_admin_ui/dist/index.html ]]; then
    (cd packages/nimbusware_admin_ui && npm ci --silent && npm test --silent)
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
  bash "${ROOT}/scripts/run_integration_like_ci.sh"
fi

if [[ "${WITH_E2E}" -eq 1 ]]; then
  poetry run pytest tests/e2e -q -m e2e
fi
