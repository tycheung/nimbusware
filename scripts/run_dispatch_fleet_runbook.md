# Enterprise Redis Fleet Worker Runbook (fo205)

Multi-node verify workers share one Redis queue (`NIMBUSWARE_RUN_DISPATCH=redis`).

## Prerequisites

- `NIMBUSWARE_EDITION=enterprise`
- Postgres + API configured (`NIMBUSWARE_DATABASE_URL`, optional DB config)
- Redis 7+ (`docker compose --profile fleet up -d redis`)

## Environment

```powershell
$env:NIMBUSWARE_EDITION = "enterprise"
$env:NIMBUSWARE_RUN_DISPATCH = "redis"
$env:NIMBUSWARE_REDIS_URL = "redis://127.0.0.1:6379/0"
# Local stack E2E (single API subprocess + memory queue): NIMBUSWARE_EMBED_DISPATCH_WORKER=1
# Redis fleet (integration): NIMBUSWARE_RUN_DISPATCH=redis NIMBUSWARE_REDIS_URL=redis://127.0.0.1:6379/0
#   poetry run pytest tests/integration/test_redis_dispatch_worker_stack.py -m integration
# Optional back-pressure thresholds (defaults: pending=100, in_flight=20)
$env:NIMBUSWARE_FLEET_QUEUE_BACKPRESSURE_DEPTH = "100"
$env:NIMBUSWARE_FLEET_QUEUE_BACKPRESSURE_IN_FLIGHT = "20"
```

## Start Redis (compose)

```bash
docker compose --profile fleet up -d redis
```

## Start workers (scale horizontally)

Run one process per machine or terminal:

```bash
poetry run python scripts/run_dispatch_worker.py
```

Bounded smoke (exits when idle):

```bash
poetry run python scripts/run_dispatch_worker.py --max-idle-loops 50 --idle-sleep-seconds 0.1
```

Heartbeat file (includes `fleet_metrics` when fleet profile is active):

`.cache/run_dispatch_worker_heartbeat.json`

## Health and metrics (Enterprise API)

Requires Enterprise IAM API key from fo201 bootstrap:

- `GET /v1/enterprise/fleet-worker/health` — queue depth, back-pressure level, worker heartbeat
- `GET /v1/enterprise/fleet-worker/metrics` — queue stats only

Back-pressure levels:

| Level | Meaning |
|-------|---------|
| `ok` | Within configured limits |
| `warn` | At or above warn thresholds |
| `critical` | At or above 2× warn thresholds |

## Safe operations

- Prefer multiple short-lived workers over one long-lived process in CI.
- Monitor `backpressure=critical` before enqueue storms.
- Drain queue with N workers; tasks are at-least-once (in-flight hash until `ack`).

## Production soak checklist

Before declaring Redis fleet dispatch production-ready:

1. Run at least two worker processes against the same `NIMBUSWARE_REDIS_URL` for 30+ minutes under queued campaign load.
2. Confirm `GET /v1/enterprise/fleet-worker/health` reports `backpressure=ok` and optional `worker_heartbeat.status=active`.
3. Verify worker heartbeat file or pod logs show monotonic `processed` counts (`scripts/run_dispatch_worker.py --heartbeat-path /tmp/worker.json`).
4. Restart one worker mid-queue; confirm remaining workers drain pending tasks without duplicate side effects (tasks are acked after processing).
5. Roll API pods after secret rotation; confirm Helm `checksum/secrets` triggers worker rollout.

## Multi-node production soak

For fleets with three or more worker nodes sharing one Redis URL:

1. Start `N` workers (`N >= 3`) on distinct hosts or pods with identical `NIMBUSWARE_REDIS_URL` and `NIMBUSWARE_RUN_DISPATCH=redis`.
2. Enqueue campaign verify load for 60+ minutes; confirm each worker heartbeat shows increasing `processed` without stuck in-flight entries.
3. Kill one worker at random intervals; verify queue depth recovers and no task executes twice (check run event dedupe).
4. Compare `GET /v1/enterprise/fleet-worker/metrics` queue depth against sum of per-worker heartbeat `processed` deltas.
5. For Redis Sentinel or clustered deployments, point all workers at the same logical primary URL; avoid split-brain by using one compose profile or Helm release per environment.

Integration reference: `tests/integration/test_redis_dispatch_worker_stack.py` and `tests/unit/test_run_dispatch.py::test_redis_dispatch_worker_loop_drains_multiple_tasks`.
