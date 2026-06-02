# Migrations (removed)

Nimbusware no longer ships numbered incremental SQL migrations. Apply the greenfield schema in ``schema/postgres.sql`` (Nimbusware platform ``nimbusware_*`` tables plus Hermes agent tables). For a **greenfield**
Postgres, apply the single bootstrap script:

[`../schema/postgres.sql`](../schema/postgres.sql)

Use [`scripts/apply_event_store.sh`](../../../scripts/apply_event_store.sh) (or
`.ps1`) from the repo root with `NIMBUSWARE_DATABASE_URL` set.
