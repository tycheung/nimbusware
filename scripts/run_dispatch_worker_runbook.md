# Run Dispatch Worker Runbook

## Local queue-drain smoke check

1. Set repo root and dispatch mode:
   - PowerShell:
     - `$env:NIMBUSWARE_REPO_ROOT = "D:\Nimbusware"`
     - `$env:HERMES_RUN_DISPATCH = "memory"`
2. Run worker with bounded idle exit:
   - `poetry run python scripts/run_dispatch_worker.py --max-idle-loops 20 --idle-sleep-seconds 0.1`
3. Verify heartbeat file was written:
   - `.cache/run_dispatch_worker_heartbeat.json`

## Redis worker start

1. Set dispatch + Redis URL:
   - `$env:HERMES_RUN_DISPATCH = "redis"`
   - `$env:HERMES_REDIS_URL = "redis://127.0.0.1:6379/0"`
2. Start one or more workers:
   - `poetry run python scripts/run_dispatch_worker.py --max-idle-loops 0`
3. For finite drain windows:
   - `poetry run python scripts/run_dispatch_worker.py --max-idle-loops 200 --idle-sleep-seconds 0.1`

## Safe shutdown guidance

- Prefer bounded runs (`--max-idle-loops`) in automation.
- Use heartbeat updates to detect wedged workers.
- Scale horizontally by launching multiple worker processes against the same Redis queue.
