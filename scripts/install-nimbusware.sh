#!/usr/bin/env bash
# Bootstrap Nimbusware: Poetry deps, Docker Postgres, schema apply.
# Usage (from repo root):
#   bash scripts/install-nimbusware.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "ERROR: python3 not found" >&2
  exit 1
fi
exec "$PY" "$ROOT/scripts/install_nimbusware.py" "$@"
