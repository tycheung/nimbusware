# Security

## Reporting vulnerabilities

If you discover a security issue, report it privately to the repository maintainers. Do not open a public issue for exploitable vulnerabilities until a fix is available.

## Secrets and credentials

| Asset | Policy |
|-------|--------|
| `.env` | Gitignored. Copy from [`.env.example`](.env.example); never commit real credentials. |
| `NIMBUSWARE_ADMIN_TOKEN` | Dev default is `nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD`. Rotate before binding the API to non-loopback hosts. `nimbusware-api` refuses the dev default on public interfaces ([`packages/nimbusware_env/admin_token.py`](packages/nimbusware_env/admin_token.py)). |
| Enterprise API keys | Stored as SHA-256 hashes; plaintext shown once at creation. Use a secret manager in production. |
| Postgres DSN | Set via `NIMBUSWARE_DATABASE_URL`; use TLS and least-privilege roles in production. |

## Authentication model

- **Individual edition:** Admin routes require `X-Nimbusware-Admin-Token`.
- **Enterprise edition:** User routes require `X-Nimbusware-Api-Key` with scoped permissions (`maker_user`, `maker_admin`).

## Network egress

Slice implement agents and scraper stages use role-gated egress allowlists in [`packages/nimbusware_executor/egress.py`](packages/nimbusware_executor/egress.py). Outbound HTTP is denied unless the actor role and target host match configured allowlists.

## Dependency and static analysis

CI runs on every PR:

- **bandit** — Python security linter (`poetry run bandit -c pyproject.toml -r packages`)
- **pip-audit** — known vulnerability scan on locked dependencies

Run locally via [`scripts/ci_check.ps1`](scripts/ci_check.ps1) or [`scripts/ci_check.sh`](scripts/ci_check.sh).

## Production checklist

See [docs/deploy/README.md](docs/deploy/README.md) for bind policy, schema migration, SBOM on release tags, and admin token rotation.
