# Long-run campaign soak (operations)

Individual ships a **24h golden replay** in CI (`tests/e2e/journeys/` slow tier). Production soak validates dispatch, Redis fleet queues, and completion eval under sustained load.

## Cadence

| Environment | Suggested frequency | Duration |
|-------------|---------------------|----------|
| Staging | Weekly (Sunday) | 4–24h autonomous campaign |
| Production | Monthly or post-release | 4h smoke + optional 24h |

## Procedure

1. Create project from golden fixture workspace (`tests/fixtures/repos/tiny_api_app` or buyer workspace).
2. `POST /v1/campaigns` with `workflow_profile=campaign_factory_zero_touch` or `campaign_micro_slice`, `autonomous=true`.
3. Enable memory dispatch: `NIMBUSWARE_RUN_DISPATCH=redis` with fleet URLs ([production-fleet-redis-secrets.md](production-fleet-redis-secrets.md)).
4. Run worker fleet: `scripts/run_dispatch_worker.py` (one consumer per Redis broker URL).
5. Monitor:
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

- Eval tuning: [../eval-tuning-guide.md](../eval-tuning-guide.md)
- Fleet Playwright: [fleet-playwright-pool.md](fleet-playwright-pool.md)
