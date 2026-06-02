# Deploying Nimbusware (Lane V4)

## Docker Compose (local / staging)

```bash
docker compose up -d postgres
docker compose --profile api up -d api
```

API listens on `http://127.0.0.1:8000`. OpenAPI: `/docs`.

Required env:

| Variable | Notes |
|----------|--------|
| `NIMBUSWARE_DATABASE_URL` | Postgres DSN (schema via `scripts/apply_event_store.sh`) |
| `NIMBUSWARE_REPO_ROOT` | Repo root inside container (`/app` in image) |
| `NIMBUSWARE_ADMIN_TOKEN` | Required for admin routes off loopback |

## Build API image only

```bash
docker build -t nimbusware-api:local .
docker run --rm -p 8000:8000 \
  -e NIMBUSWARE_DATABASE_URL=postgresql://nimbusware:nimbusware@host.docker.internal:5432/nimbusware \
  -e NIMBUSWARE_REPO_ROOT=/app \
  nimbusware-api:local
```

Apply schema on the host before first run:

```bash
NIMBUSWARE_DATABASE_URL=postgresql://nimbusware:nimbusware@127.0.0.1:5432/nimbusware \
  bash scripts/apply_event_store.sh
```

## Secrets

- Never ship the dev default admin token in production.
- Enterprise edition: bootstrap IAM keys via Postgres (`nimbusware_iam`) or admin API; store keys in a secret manager.

## Worker (optional)

Redis fleet dispatch uses `hermes-run-worker` on the host or a separate container — see `scripts/run_dispatch_fleet_runbook.md`.

## Kubernetes

Reference manifests: [k8s/](k8s/README.md).

## OIDC (Enterprise console)

Design note: [oidc.md](oidc.md) — API keys remain; IdP login is a console-layer addition.

## External SLI

Fleet Ollama SLI: `scripts/fleet_ollama_sli_runbook.md` and `poetry run hermes-fleet-ollama-sli`.
