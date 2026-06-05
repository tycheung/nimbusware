# Deploying Nimbusware

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

## CI (GitHub Actions)

- **Unit** — default PR job (`ci.yml`): ruff, mypy, pytest unit subset @ 75% coverage.
- **Integration** — Postgres `-m integration` on PR.
- **E2E** — `tests/e2e -m e2e` on PR (import smoke + API `run.created` with Postgres).
- **Weekly** — `e2e_smoke.yml`, `swe_bench.yml` (dry-run layout check + required scored `--run` with `min_pass_rate: 1.0`).
- **Quarterly / manual** — `k8s_reference_smoke.yml` (`kubectl apply --dry-run=client` on [`docs/deploy/k8s/`](k8s/README.md) manifests).
- **PR / manual** — `oidc_smoke.yml` (mock Enterprise OIDC session tests).

## Secrets

- Never ship the dev default admin token in production (`nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD`).
- Set `NIMBUSWARE_ADMIN_TOKEN` to a high-entropy secret before binding the API off loopback; `nimbusware-api` calls `require_non_default_admin_token_for_host()` and exits on unsafe defaults.
- Enterprise edition: bootstrap IAM keys via Postgres (`nimbusware_iam`) or admin API; store keys in a secret manager.

## Production checklist

| Check | Command / reference |
|-------|---------------------|
| CI parity | `./scripts/ci_check.ps1` or `ci_check.sh` (see [CONTRIBUTING.md](../../CONTRIBUTING.md)) |
| Schema applied | `scripts/apply_event_store.sh` |
| Admin token rotated | `NIMBUSWARE_ADMIN_TOKEN` not the dev default |
| API bind policy | Loopback-only unless token is production-grade |
| SBOM on release | Tag `v*` triggers `.github/workflows/sbom.yml` |
| Dependency audit | `poetry run pip-audit` (also in CI) |

## Worker (optional)

Redis fleet dispatch uses `hermes-run-worker` on the host or a separate container — see `scripts/run_dispatch_fleet_runbook.md`.

## Kubernetes

Reference manifests: [k8s/](k8s/README.md).

## OIDC (Enterprise console)

Implemented console gate: [oidc.md](oidc.md) — API keys remain; IdP login is a console-layer addition (`NIMBUSWARE_OIDC_*`).

## Release SBOM

Tag pushes (`v*`) run `.github/workflows/sbom.yml` and fail on SBOM generation errors.
Use the uploaded `sbom.cdx.json` artifact as the release bill of materials.

## External SLI

Fleet Ollama SLI: `scripts/fleet_ollama_sli_runbook.md` and `poetry run hermes-fleet-ollama-sli`.
