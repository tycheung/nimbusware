#!/usr/bin/env bash
# Match CI integration job: apply packages/nimbusware_store/schema/postgres.sql then pytest -m integration.
# Usage:
#   export NIMBUSWARE_DATABASE_URL="postgresql://nimbusware:nimbusware@127.0.0.1:5432/nimbusware"
#   export NIMBUSWARE_REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"  # optional
#   ./scripts/ci/run_integration_like_ci.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export NIMBUSWARE_REPO_ROOT="${NIMBUSWARE_REPO_ROOT:-$ROOT}"
export NIMBUSWARE_SKIP_PREFLIGHT="${NIMBUSWARE_SKIP_PREFLIGHT:-1}"
bash "$ROOT/scripts/database/apply_event_store.sh"
cd "$ROOT"
poetry run pytest tests -q -m integration
