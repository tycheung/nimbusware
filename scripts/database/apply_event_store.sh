#!/usr/bin/env bash
# Drop public schema and apply Nimbusware PostgreSQL bootstrap (greenfield).
# Usage: NIMBUSWARE_DATABASE_URL=postgresql://user:pass@host:5432/dbname ./scripts/database/apply_event_store.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RESET="$ROOT/packages/store/schema/reset_public.sql"
SQL="$ROOT/packages/store/schema/postgres.sql"
: "${NIMBUSWARE_DATABASE_URL:?NIMBUSWARE_DATABASE_URL is not set}"
psql "$NIMBUSWARE_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$RESET"
psql "$NIMBUSWARE_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$SQL"
echo "Reset and applied: $SQL"
