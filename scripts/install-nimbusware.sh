#!/usr/bin/env bash
# Entry point wrapper — implementation in scripts/install/install-nimbusware.sh
set -euo pipefail
exec "$(cd "$(dirname "$0")" && pwd)/install/install-nimbusware.sh" "$@"
