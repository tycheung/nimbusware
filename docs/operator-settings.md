# Operator settings

Environment variables and flags are grouped by **access grain**. Managed values live in Postgres (`operator_settings` namespace); install secrets stay in `.env`.

## Scopes

| Scope | Who edits | Storage | UI |
|-------|-----------|---------|-----|
| **install** | Operator / installer | `.env` only | Read-only in Admin Console |
| **system** | Admin | Postgres `operator_settings/system` | Admin Console → Operator settings |
| **user** | Maker (per machine/profile) | Postgres `operator_settings/user` | Maker → Settings |
| **run** | End user per run | `run.created` metadata `operator_settings` | `POST /v1/runs` body |

## Resolution order

For catalog keys: **run override → user profile → system defaults → process env → catalog default**.

API startup loads system + user documents into `os.environ` for backward compatibility with direct `os.environ` reads.

## API

- `GET /v1/settings/catalog` — full catalog by scope
- `GET /v1/settings/install` — masked install profile
- `GET/PATCH /v1/settings/system` — admin token required
- `GET/PATCH /v1/settings/me` — user profile
- `POST /v1/runs` — optional `operator_settings` map (run-scoped keys)

## Implementation

- Catalog: `packages/nimbusware_env/settings_catalog.py`
- Store: `packages/nimbusware_env/settings_store.py`
- Resolver: `packages/nimbusware_env/settings_resolve.py`

Add new tunables to the catalog first, then wire reads through `settings_resolve` or `env_flags` helpers.
