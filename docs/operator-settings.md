# Operator settings

Environment variables and flags are grouped by **access grain**. Managed values live in Postgres (`operator_settings` namespace); install secrets stay in `.env`.

## Scopes

| Scope | Who edits | Storage | UI |
|-------|-----------|---------|-----|
| **install** | Operator / installer | `.env` only | Admin read-only |
| **system** | Admin | Postgres `operator_settings/system` | Admin Console → Operator settings |
| **user** | Maker | Postgres `operator_settings/user` | Maker → Settings |
| **run** | Per run | `run.created` metadata | `POST /v1/runs` `operator_settings` |
| **internal** | CI/dev only | Not stored | None (audit-allowlisted) |

## Resolution order

For managed keys: **run override → user profile → system defaults → process env → catalog default**.

YAML override knobs (universal critique): only explicit `os.environ` or run overrides replace workflow YAML — catalog defaults do not.

Fail-closed §14 keys (`HERMES_SKIP_PREFLIGHT`, `HERMES_RUN_BANDIT`, `HERMES_OUTBOUND_FETCH_ENABLED`, `HERMES_PREFLIGHT_JSON_PROBE`) use raw env reads after Postgres sync on startup.

## API

- `GET /v1/settings/catalog`
- `GET/PATCH /v1/settings/system` (admin)
- `GET/PATCH /v1/settings/me` (user)

## CI guard

`scripts/audit_operator_env.py` runs in `scripts/ci_check.ps1`. Every `HERMES_*` / `NIMBUSWARE_*` / `OLLAMA_HOST` / `PORT` read under `packages/` must be cataloged or in a bootstrap allowlist.

## Implementation

- Catalog: `packages/nimbusware_env/settings_catalog.py` + `settings_catalog_extended.py` (~140 keys)
- Store: `packages/nimbusware_env/settings_store.py`
- Resolver: `packages/nimbusware_env/settings_resolve.py`
- Helpers: `packages/nimbusware_env/env_flags.py`

Add new tunables to the catalog first, then read via `env_flags` / `settings_resolve`.
