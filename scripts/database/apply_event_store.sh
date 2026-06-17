#!/usr/bin/env bash
# Apply Nimbusware PostgreSQL bootstrap schema (single file, greenfield).
# Usage: NIMBUSWARE_DATABASE_URL=postgresql://user:pass@host:5432/dbname ./scripts/apply_event_store.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SQL="$ROOT/packages/nimbusware_store/schema/postgres.sql"
: "${NIMBUSWARE_DATABASE_URL:?NIMBUSWARE_DATABASE_URL is not set}"
psql "$NIMBUSWARE_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$SQL"
echo "Applied: $SQL"
