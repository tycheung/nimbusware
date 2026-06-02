# Reference Kubernetes manifests (Lane V5)

Not production-hardened — starting point for Enterprise ops.

## Apply order

1. Create namespace and secrets (`api-secrets.yaml` — fill DSN and admin token).
2. `kubectl apply -f postgres.yaml` (or use managed Postgres and skip).
3. Run `scripts/apply_event_store.sh` against the DSN once.
4. `kubectl apply -f api-deployment.yaml`

## Files

| File | Purpose |
|------|---------|
| `api-secrets.yaml` | DSN + admin token placeholders |
| `api-deployment.yaml` | API Deployment + ClusterIP Service |

Worker / Redis fleet dispatch is documented in `scripts/run_dispatch_fleet_runbook.md` — add a Deployment when `HERMES_RUN_DISPATCH=redis`.
