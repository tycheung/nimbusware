#!/usr/bin/env bash
# Apply Hermes PostgreSQL bootstrap schema (single file, greenfield).
# Usage: HERMES_DATABASE_URL=postgresql://user:pass@host:5432/dbname ./scripts/apply_event_store.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SQL="$ROOT/packages/hermes_store/schema/postgres.sql"
: "${HERMES_DATABASE_URL:?HERMES_DATABASE_URL is not set}"
psql "$HERMES_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$SQL"
echo "Applied: $SQL"
