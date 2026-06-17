# Production multi-host Redis fleet secrets

Guide for wiring **multi-broker Redis dispatch** (`NIMBUSWARE_REDIS_FLEET_URLS`) in production Kubernetes / Helm deployments.

## When to use fleet URLs

| Scenario | Configuration |
|----------|----------------|
| Single in-cluster Redis | `NIMBUSWARE_REDIS_URL=redis://redis:6379/0` (Helm default when `redis.enabled`) |
| Managed Redis (one endpoint) | `secrets.redisUrl` in Helm values |
| **Multi-host fleet** (primary + replica brokers, regional shards) | `secrets.redisFleetUrls` comma-separated list |

Fleet URLs power weekly **redis-fleet-soak** CI (`NIMBUSWARE_REDIS_FLEET_URLS=redis://127.0.0.1:6379/0,redis://127.0.0.1:6380/0`) and production worker drain across brokers. See [`scripts/runbooks/e2e_redis_fleet_soak_runbook.md`](../../scripts/runbooks/e2e_redis_fleet_soak_runbook.md).

## Helm values (recommended)

```bash
helm upgrade nimbusware charts/nimbusware \
  --set edition=enterprise \
  --set worker.enabled=true \
  --set redis.enabled=false \
  --set secrets.redisFleetUrls='rediss://primary.example.com:6379/0,rediss://replica.example.com:6379/0' \
  --set secrets.databaseUrl='postgresql://...' \
  --set secrets.adminToken='...'
```

When `redisFleetUrls` is set, API and worker pods receive:

| Env | Value |
|-----|--------|
| `NIMBUSWARE_RUN_DISPATCH` | `redis` |
| `NIMBUSWARE_REDIS_FLEET_URLS` | Comma-separated fleet list |
| `NIMBUSWARE_REDIS_URL` | First URL in the fleet (primary) |

Use `rediss://` for TLS-terminated managed Redis. Store credentials in the secret manager; inject via `helm upgrade --set secrets.redisFleetUrls=...` or an external-secrets operator — **never** commit URLs with passwords to git.

## Raw Kubernetes secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: nimbusware-api-secrets
type: Opaque
stringData:
  NIMBUSWARE_DATABASE_URL: postgresql://...
  NIMBUSWARE_ADMIN_TOKEN: ...
  NIMBUSWARE_REDIS_FLEET_URLS: rediss://primary:6379/0,rediss://replica:6379/0
  NIMBUSWARE_REDIS_URL: rediss://primary:6379/0
```

Both API and worker deployments must mount the same secret and set `NIMBUSWARE_RUN_DISPATCH=redis`.

## Verification

1. **Pre-rollout soak** — with VPN/firewall open to brokers:
   ```bash
   export NIMBUSWARE_REDIS_FLEET_URLS='rediss://primary:6379/0,rediss://replica:6379/0'
   poetry run python scripts/ops/run_redis_fleet_soak_ci.py
   ```
2. **Worker health** — Enterprise Admin **Fleet** tab: worker queue depth and heartbeat.
3. **Campaign tick** — start `campaign_micro_slice`; confirm `campaign_driver_tick` events on timeline.

## Rotation

1. Add new broker URL to `redisFleetUrls` (comma-append).
2. `helm upgrade` — checksum annotation rolls API + worker pods.
3. Drain old broker queues before removing its URL from the list.

## Security

- Least-privilege Redis ACL per Nimbusware service account.
- Separate logical DB indexes (`/0`, `/1`) per environment.
- No plaintext Redis passwords in `values.yaml` checked into git — use CI/CD secret injection.

## Related

- [`scripts/runbooks/e2e_redis_fleet_soak_runbook.md`](../../scripts/runbooks/e2e_redis_fleet_soak_runbook.md)
- [`scripts/runbooks/run_dispatch_fleet_runbook.md`](../../scripts/runbooks/run_dispatch_fleet_runbook.md)
- [helm.md](helm.md)
