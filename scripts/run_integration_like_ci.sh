#!/usr/bin/env bash
# Match CI integration job: apply packages/hermes_store/schema/postgres.sql then pytest -m integration.
# Usage:
#   export HERMES_DATABASE_URL="postgresql://hermes:hermes@127.0.0.1:5432/hermes"
#   export HERMES_REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"  # optional
#   ./scripts/run_integration_like_ci.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export HERMES_REPO_ROOT="${HERMES_REPO_ROOT:-$ROOT}"
export HERMES_SKIP_PREFLIGHT="${HERMES_SKIP_PREFLIGHT:-1}"
bash "$ROOT/scripts/apply_event_store.sh"
cd "$ROOT"
poetry run pytest tests -q -m integration
