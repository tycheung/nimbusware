#!/usr/bin/env bash
# Entry point wrapper — implementation in scripts/database/apply_event_store.sh
set -euo pipefail
exec "$(cd "$(dirname "$0")" && pwd)/database/apply_event_store.sh" "$@"
