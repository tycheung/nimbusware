# Migrations (removed)

Hermes no longer ships numbered incremental SQL migrations. For a **greenfield**
Postgres, apply the single bootstrap script:

[`../schema/postgres.sql`](../schema/postgres.sql)

Use [`scripts/apply_event_store.sh`](../../../scripts/apply_event_store.sh) (or
`.ps1`) from the repo root with `HERMES_DATABASE_URL` set.
