# Redis fleet stack soak (ops)

Production-style validation for multi-process Redis dispatch: API subprocess plus worker subprocess share one Redis queue.

## Local / staging run

Requires live Redis (`NIMBUSWARE_REDIS_URL`, default `redis://127.0.0.1:6379/0`):

```powershell
$env:NIMBUSWARE_REDIS_URL = "redis://127.0.0.1:6379/0"
poetry run pytest tests/integration/test_redis_dispatch_worker_stack.py -m "integration and e2e_stack" -q
```

## What it checks

1. API subprocess with `NIMBUSWARE_RUN_DISPATCH=redis`
2. Worker subprocess drains the shared verify queue
3. Autonomous `campaign_micro_slice` run makes progress

## CI

Weekly **redis-fleet-soak** job in [`.github/workflows/slow_tests.yml`](../.github/workflows/slow_tests.yml) runs `scripts/run_redis_fleet_soak_ci.py` against one or more Redis URLs (`NIMBUSWARE_REDIS_FLEET_URLS`, default `NIMBUSWARE_REDIS_URL`). CI uses two Redis service containers on ports 6379 and 6380. Local runs skip gracefully when Redis is unreachable.

Opt-in integration job only (`@pytest.mark.integration`); not part of default PR unit job. Run before fleet rollouts or after Redis/worker config changes.
