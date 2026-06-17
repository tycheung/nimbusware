# Long-run campaign soak (operations)

Individual ships a **24h golden replay** in CI (`tests/e2e/journeys/` slow tier). Production soak validates dispatch, Redis fleet queues, and completion eval under sustained load.

## Cadence

| Environment | Suggested frequency | Duration |
|-------------|---------------------|----------|
| Staging | Weekly (Sunday) | 4–24h autonomous campaign |
| Production | Monthly or post-release | 4h smoke + optional 24h |

## Automated staging (CI)

Weekly **slow_tests.yml** jobs:

| Job | Script | Purpose |
|-----|--------|---------|
| `campaign-soak-preflight` | `run_campaign_soak_check.py` | Redis + Enterprise dispatch prerequisites |
| `campaign-soak` | `run_campaign_soak.py` | Bounded campaign journey replay (2 passes) |
| `redis-fleet-soak` | `run_redis_fleet_soak_ci.py` | Multi-broker dispatch stack |
| `dev-env-weekly-soak` | `run_dev_env_weekly_soak.py` | Persistent dev-env journey |

Local smoke (matches staging):

```bash
NIMBUSWARE_EDITION=enterprise NIMBUSWARE_RUN_DISPATCH=redis \
  NIMBUSWARE_REDIS_URL=redis://127.0.0.1:6379/0 \
  python scripts/ops/run_campaign_soak.py
```

Production: run the same script monthly post-release with buyer workspace env vars, or apply [`k8s/campaign-soak-cronjob.yaml`](k8s/campaign-soak-cronjob.yaml) for in-cluster scheduling.

## Procedure

1. **Preflight** — `python scripts/ops/run_campaign_soak_check.py` (Redis fleet reachable, `NIMBUSWARE_RUN_DISPATCH=redis`, Enterprise edition). For integration depth, run `python scripts/ops/run_redis_fleet_soak_ci.py` in staging first.
2. Create project from golden fixture workspace (`tests/fixtures/repos/tiny_api_app` or buyer workspace).
3. `POST /v1/campaigns` with `workflow_profile=campaign_factory_zero_touch` or `campaign_micro_slice`, `autonomous=true`.
4. Enable memory dispatch: `NIMBUSWARE_RUN_DISPATCH=redis` with fleet URLs ([production-fleet-redis-secrets.md](production-fleet-redis-secrets.md)).
5. Run worker fleet: `scripts/ops/run_dispatch_worker.py` (one consumer per Redis broker URL).
6. Monitor:
   - `GET /v1/runs/{id}/timeline` — `campaign.tick`, maintenance passes, `factory.gate`, `launch_eval.completed`
   - Queue depth via Redis `LLEN` on dispatch keys
   - Maker push notifications when VAPID keys configured

## Stop conditions

- `run.completed` or `run.failed` terminal event
- Manual `POST /v1/campaigns/{id}/cancel` (lifecycle route)
- Factory `factory.gate` blocking list unchanged for >N hours (investigate stuck PUT pool)

## Artifacts

Export theater transcript (`GET /v1/runs/{id}/theater/export`) and factory evidence zip after soak. Attach timeline JSON to incident tickets.

## Related

- Kubernetes reference manifests: [k8s/README.md](k8s/README.md) (`api-secrets.yaml` fleet keys, worker optional env)
- Eval tuning: [../eval-tuning-guide.md](../eval-tuning-guide.md)
- Fleet Playwright: [fleet-playwright-pool.md](fleet-playwright-pool.md)
