#!/usr/bin/env bash
# Entry point wrapper — implementation in scripts/ci/ci_check.sh
set -euo pipefail
exec "$(cd "$(dirname "$0")" && pwd)/ci/ci_check.sh" "$@"
