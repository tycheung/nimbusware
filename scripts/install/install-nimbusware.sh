#!/usr/bin/env bash
# Bootstrap Nimbusware: Poetry deps, Docker Postgres, schema apply.
# Usage (from repo root):
#   bash scripts/install-nimbusware.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
INSTALL="$ROOT/scripts/install_nimbusware.py"

if command -v poetry >/dev/null 2>&1; then
  exec poetry run python "$INSTALL" "$@"
fi

if [[ -x "$ROOT/.venv/bin/python3" ]]; then
  exec "$ROOT/.venv/bin/python3" "$INSTALL" "$@"
fi
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  exec "$ROOT/.venv/bin/python" "$INSTALL" "$@"
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$INSTALL" "$@"
fi
if command -v python >/dev/null 2>&1; then
  exec python "$INSTALL" "$@"
fi

echo "ERROR: python3 not found" >&2
exit 1
