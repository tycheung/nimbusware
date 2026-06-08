# ADR 009: Persistent dev environment sessions

## Status

Accepted — Individual v2.1 ship path uses workspace-scoped session supervisor with on-disk `session.json`.

## Context

Ephemeral PUT preview (fo651) restarts on every factory cadence pass. Operators need uvicorn/npm dev servers to stay up across slices for incremental regression.

## Decision

1. `DevEnvironmentSession` persisted under `.nimbusware/dev_env/session.json`.
2. Supervisor emits `dev_env.started` / `dev_env.stopped` timeline stages.
3. Attach mode via `NIMBUSWARE_DEV_ENV_BASE_URL` or `NIMBUSWARE_PUT_BASE_URL`.
4. HTTP API: `POST/GET /v1/runs/{id}/dev-env/*`.

## Consequences

- Factory cadence may call regression without start/stop churn when session healthy.
- Session file is workspace-local; fleet replicas need shared workspace or attach mode.
