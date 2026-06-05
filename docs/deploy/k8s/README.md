# Reference Kubernetes manifests (Lane V5)

**Production installs:** use the Helm chart at [`charts/nimbusware`](../../charts/nimbusware) ([helm.md](../helm.md)). This directory is a **raw YAML reference** for operators who prefer `kubectl apply` or need to diff against chart templates.

Not production-hardened — starting point for Enterprise ops. CI verifies manifests with `kubectl apply --dry-run=client` and `helm lint` via `.github/workflows/k8s_reference_smoke.yml` (quarterly cron + manual dispatch).

## End-to-end install path

1. **Postgres** — Production: managed Postgres DSN. Lab only: `kubectl apply -f postgres-deployment.yaml` (emptyDir, `nimbusware.io/lab-only` label).
2. **Secrets** — Edit `api-secrets.yaml`: set `NIMBUSWARE_DATABASE_URL` (host `postgres` when using lab manifest) and `NIMBUSWARE_ADMIN_TOKEN`. `kubectl apply -f api-secrets.yaml`.
3. **Redis** — `kubectl apply -f redis-deployment.yaml` (required when `HERMES_RUN_DISPATCH=redis`).
4. **Schema** — `kubectl apply -f schema-job.yaml`; wait for Job `Complete` (runs `scripts/apply_event_store.sh` / greenfield `postgres.sql`).
5. **API** — `kubectl apply -f api-deployment.yaml`. Maker PWA: `/v1/maker/app/`. Admin UI: `/v1/admin/app/` (Enterprise fleet: `/v1/admin/app/fleet`). Both ship in the API image.
6. **Worker (optional)** — `kubectl apply -f worker-deployment.yaml` when edition is Enterprise and dispatch mode is Redis (`NIMBUSWARE_EDITION=enterprise`, `HERMES_RUN_DISPATCH=redis`, `HERMES_REDIS_URL`).

## Apply order (quick)

1. Postgres (managed or `postgres-deployment.yaml` for lab).
2. `api-secrets.yaml`
3. `redis-deployment.yaml`
4. `schema-job.yaml` (wait for completion)
5. `api-deployment.yaml`
6. Optional `worker-deployment.yaml`

## Files

| File | Purpose |
|------|---------|
| `api-secrets.yaml` | DSN + admin token placeholders |
| `postgres-deployment.yaml` | **Lab/non-prod** in-cluster Postgres + Service `postgres` |
| `api-deployment.yaml` | API Deployment + ClusterIP Service |
| `redis-deployment.yaml` | Redis 7 for fleet worker queue |
| `worker-deployment.yaml` | `run_dispatch_worker.py` (enterprise + redis dispatch) |
| `schema-job.yaml` | One-shot schema apply via `scripts/apply_event_store.sh` |
| `console-deployment.yaml` | Legacy note only — Admin UI ships with API (`/v1/admin/app/`) |

## Environment matrix

| Component | Required env |
|-----------|----------------|
| API | `NIMBUSWARE_DATABASE_URL`, `NIMBUSWARE_REPO_ROOT`, secrets ref |
| Worker | Above + `NIMBUSWARE_EDITION=enterprise`, `HERMES_RUN_DISPATCH=redis`, `HERMES_REDIS_URL` |
| Schema job | `NIMBUSWARE_DATABASE_URL` via secrets |
| Console | `NIMBUSWARE_API_BASE`, admin token in secrets |

Worker / Redis fleet dispatch is also documented in `scripts/run_dispatch_fleet_runbook.md`.
