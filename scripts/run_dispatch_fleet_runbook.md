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
