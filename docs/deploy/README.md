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
| `NIMBUSWARE_DATABASE_URL` | Postgres DSN (schema via `scripts/database/apply_event_store.sh`) |
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
  bash scripts/database/apply_event_store.sh
```

## CI (GitHub Actions)

- **Unit** — default PR job (`ci.yml`): ruff, mypy, pytest unit subset @ 75% coverage.
- **Integration** — Postgres `-m integration` on PR.
- **E2E** — `tests/e2e -m e2e` on PR (import smoke + API `run.created` with Postgres).
- **Weekly** — `slow_tests.yml` (`-m slow`, stack-soak, redis-fleet-soak, factory-weekly, **dev-env-weekly-soak**); `e2e_smoke.yml`, `swe_bench.yml` (dry-run layout check + required scored `--run` with `min_pass_rate: 1.0`).
- **Quarterly / manual** — `k8s_reference_smoke.yml` (`helm lint` + `kubectl apply --dry-run=client` on [`docs/deploy/k8s/`](k8s/README.md) manifests).
- **Weekly / manual** — `ssh_hardware_probe.yml` (Enterprise fleet SSH tier probe; [runbook](ssh-hardware-probe.md)).
- **PR / manual** — `oidc_smoke.yml` (mock Enterprise OIDC session tests).
- **Optional ops** — Enterprise integrator gate + live probe: [enterprise-integrator-runbook.md](enterprise-integrator-runbook.md); GitHub Checks or GitLab commit status bridge (integrator, slice.gate, factory.gate): [external-ci-bridge.md](external-ci-bridge.md); headless patch from CI: [headless-patch-ci.md](headless-patch-ci.md).
- **Launcher releases** — `publish_launcher.yml` on tag `launcher-v*` or manual dispatch; see [launcher.md](launcher.md).

## Secrets

- Multi-host Redis fleet brokers: [production-fleet-redis-secrets.md](production-fleet-redis-secrets.md) (`NIMBUSWARE_REDIS_FLEET_URLS` in Helm values).
- Never ship the dev default admin token in production (`nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD`).
- Set `NIMBUSWARE_ADMIN_TOKEN` to a high-entropy secret before binding the API off loopback; `nimbusware-api` calls `require_non_default_admin_token_for_host()` and exits on unsafe defaults.
- Enterprise edition: bootstrap IAM keys via Postgres (`nimbusware_iam`) or admin API; store keys in a secret manager.

## Production checklist

| Check | Command / reference |
|-------|---------------------|
| CI parity | `./scripts/ci/ci_check.ps1` or `ci_check.sh` (see [CONTRIBUTING.md](../../CONTRIBUTING.md)) |
| Schema applied | `scripts/database/apply_event_store.sh` |
| Admin token rotated | `NIMBUSWARE_ADMIN_TOKEN` not the dev default |
| API bind policy | Loopback-only unless token is production-grade |
| SBOM on release | Tag `v*` triggers `.github/workflows/sbom.yml` |
| Dependency audit | `poetry run pip-audit` (also in CI) |

## Worker (optional)

Redis fleet dispatch uses `nimbusware-run-worker` on the host or a separate container — see `scripts/runbooks/run_dispatch_fleet_runbook.md`.

## Production ops runbooks

| Topic | Doc |
|-------|-----|
| Helm ingress + TLS | [helm.md](helm.md) — wire `ingress.hosts`, cert-manager or cloud LB TLS before exposing API off loopback |
| Fleet Redis secrets | [production-fleet-redis-secrets.md](production-fleet-redis-secrets.md) |
| Remote Playwright pool | [fleet-playwright-pool.md](fleet-playwright-pool.md) — set `NIMBUSWARE_FLEET_PLAYWRIGHT_WS_ENDPOINT` on API + workers |
| Long-run campaign soak | [campaign-soak-runbook.md](campaign-soak-runbook.md) — preflight `run_campaign_soak_check.py`, execution `run_campaign_soak.py`, optional [`k8s/campaign-soak-cronjob.yaml`](k8s/campaign-soak-cronjob.yaml) |
| Persistent dev-env journey soak | [`scripts/ops/run_dev_env_weekly_soak.py`](../../scripts/ops/run_dev_env_weekly_soak.py) (weekly **dev-env-weekly-soak** in `slow_tests.yml`) |

**Staging → production checklist:** apply schema, rotate admin token, enable Helm ingress TLS ([helm.md](helm.md)), configure fleet Redis + worker fleet ([production-fleet-redis-secrets.md](production-fleet-redis-secrets.md)), attach remote Playwright when factory tiers run concurrently ([fleet-playwright-pool.md](fleet-playwright-pool.md)), then schedule campaign soak per [campaign-soak-runbook.md](campaign-soak-runbook.md).

## Kubernetes

Production Helm chart: [helm.md](helm.md) (`charts/nimbusware`). Raw reference manifests: [k8s/](k8s/README.md) (ingress, NetworkPolicy, HPA, PDB, suspended event-store purge CronJob). Event store retention policy: [event-store-retention.md](event-store-retention.md).

## OIDC (Enterprise console)

Implemented console gate: [oidc.md](oidc.md) — API keys remain; IdP login is a console-layer addition (`NIMBUSWARE_OIDC_*`).

## Release SBOM

Tag pushes (`v*`) run `.github/workflows/sbom.yml` and fail on SBOM generation errors.
Use the uploaded `sbom.cdx.json` artifact as the release bill of materials.

## External SLI

Fleet Ollama SLI: `scripts/runbooks/fleet_ollama_sli_runbook.md` and `poetry run nimbusware-fleet-ollama-sli`.

## First publish (PyPI + VSCE)

Build-only preflight (no tokens required):

```bash
poetry run python scripts/publish/first_publish_gates.py
```

Upload when secrets are configured (`PYPI_API_TOKEN`, `VSCE_PAT`): [pypi-publish.md](pypi-publish.md), [vscode-marketplace.md](vscode-marketplace.md).

## Agent sandbox

Individual (`none`/`stub`/`docker`) and Enterprise (`kubernetes`/`e2b`) backends: [agent-sandbox.md](agent-sandbox.md).
