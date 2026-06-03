# Reference Kubernetes manifests (Lane V5)

Not production-hardened — starting point for Enterprise ops.

## Apply order

1. Provision Postgres (managed service recommended — no `postgres.yaml` in this repo).
2. Create namespace and secrets (`api-secrets.yaml` — fill DSN and admin token).
3. `kubectl apply -f redis-deployment.yaml` (fleet dispatch).
4. `kubectl apply -f schema-job.yaml` and wait for completion (greenfield `postgres.sql`).
5. `kubectl apply -f api-deployment.yaml`
6. Optional: `kubectl apply -f worker-deployment.yaml` when `HERMES_RUN_DISPATCH=redis`.
7. Optional: `kubectl apply -f console-deployment.yaml` for Admin Console (Streamlit).

## Files

| File | Purpose |
|------|---------|
| `api-secrets.yaml` | DSN + admin token placeholders |
| `api-deployment.yaml` | API Deployment + ClusterIP Service |
| `redis-deployment.yaml` | Redis 7 for fleet worker queue |
| `worker-deployment.yaml` | `run_dispatch_worker.py` (enterprise + redis dispatch) |
| `schema-job.yaml` | One-shot schema apply via `scripts/apply_event_store.sh` |
| `console-deployment.yaml` | Optional Admin Console (not production-hardened) |

## Environment matrix

| Component | Required env |
|-----------|----------------|
| API | `NIMBUSWARE_DATABASE_URL`, `NIMBUSWARE_REPO_ROOT`, secrets ref |
| Worker | Above + `NIMBUSWARE_EDITION=enterprise`, `HERMES_RUN_DISPATCH=redis`, `HERMES_REDIS_URL` |
| Schema job | `NIMBUSWARE_DATABASE_URL` via secrets |
| Console | `NIMBUSWARE_API_BASE`, admin token in secrets |

Worker / Redis fleet dispatch is also documented in `scripts/run_dispatch_fleet_runbook.md`.
