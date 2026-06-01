#!/usr/bin/env bash
# Mirror the default CI unit job locally (see .github/workflows/ci.yml).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export HERMES_SKIP_PREFLIGHT="${HERMES_SKIP_PREFLIGHT:-1}"

poetry run python scripts/rebuild_bundle_faiss_if_stale.py --dry-run
poetry run ruff check packages tests
poetry run mypy packages
poetry run bandit -r packages -lll -q
poetry run pytest tests -q -m "not integration and not slow and not benchmark" \
  --cov=packages \
  --cov-report=term-missing:skip-covered \
  --cov-fail-under=72
