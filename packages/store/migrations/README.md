# Migrations (removed)

Nimbusware no longer ships numbered incremental SQL migrations. Apply the greenfield schema in ``schema/postgres.sql`` (``nimbusware_*`` platform tables plus agent run tables). Schema apply **drops and recreates** the ``public`` schema first (``reset_public.sql``) so stale tables cannot drift from the bootstrap file.

For a **greenfield** Postgres, apply the single bootstrap script:

[`../schema/postgres.sql`](../schema/postgres.sql)

Use [`scripts/database/apply_event_store.sh`](../../../scripts/database/apply_event_store.sh) (or
`.ps1`) from the repo root with `NIMBUSWARE_DATABASE_URL` set. That always
runs [`../schema/reset_public.sql`](../schema/reset_public.sql) then
[`../schema/postgres.sql`](../schema/postgres.sql).

**Existing databases:** re-running the apply scripts wipes all public-schema
objects and recreates them. When only `event_store_type_allowed` CHECK values
need updating without a full wipe, alter that constraint to match `agent_core`
`EventType` in `packages/agent_core/models/events_foundation.py`.
