# Enterprise buyer checklist

One-page summary for security and platform reviewers evaluating Nimbusware **Enterprise** edition.

## Identity and access

| Control | Implementation |
|---------|----------------|
| API authentication | `X-Nimbusware-Api-Key` on all routes; scopes `maker_user` / `maker_admin` |
| IAM audit trail | Postgres-backed IAM action log; included in enterprise audit export |
| Admin Console SSO | Optional OIDC shell (`docs/deploy/oidc.md`); API calls still require keys/tokens |
| Tenant isolation | Row-level isolation on events, config, and memory when IAM is enabled |

## Data and audit

| Control | Implementation |
|---------|----------------|
| Run auditability | Append-only event store (`nimbusware_store`); per-run `GET /v1/runs/{id}/audit-export` |
| Enterprise export | `GET /v1/enterprise/audit-export` — IAM actions, event index, research/egress ledgers |
| Egress policy | Role-gated allowlists in `nimbusware_executor.egress` |
| Research index | Tenant JSONL under `.nimbusware/enterprise/{tenant}/` — `docs/enterprise-research-index.md` |

## Fleet and operations

| Control | Implementation |
|---------|----------------|
| Fleet memory | `GET /v1/enterprise/fleet-memory/*` — org-scoped index + canonical sync |
| Config propagation | Postgres `LISTEN/NOTIFY` + `config.document.updated` invalidation |
| Worker health | Redis dispatch worker metrics; Admin **Fleet** tab at `/v1/admin/app/fleet` |
| Hardware tiers | Local + optional SSH fleet probe; weekly scheduled workflow with failure alerts ([`docs/deploy/ssh-hardware-probe.md`](deploy/ssh-hardware-probe.md)) |

## Supply chain

| Control | Implementation |
|---------|----------------|
| CI security | `bandit` + `pip-audit` in every PR (`scripts/ci_check.ps1`) |
| Release SBOM | Tag `v*` triggers `.github/workflows/sbom.yml` |
| Dependency lock | `poetry.lock` pinned in repo |

## Regulated / air-gapped bundle

For teams that cannot use SaaS coding agents or cloud LLM defaults:

| Requirement | Nimbusware control |
|-------------|-------------------|
| No cloud LLM by default | Individual edition uses Ollama-only `model-routing.yaml`; hybrid cloud is **opt-in** via routing presets |
| Egress control | `nimbusware_executor.egress` role allowlists + domain budgets |
| Agent sandbox | [deploy/agent-sandbox.md](deploy/agent-sandbox.md) — jail + tool caps on writer roles |
| Audit trail | Per-run `GET /v1/runs/{id}/audit-export`; fleet `GET /v1/enterprise/audit-export` |
| Self-hosted deploy | Helm chart [`charts/nimbusware`](../charts/nimbusware) — set `edition: enterprise`, wire `secrets.databaseUrl`, disable external object stores unless approved |
| External CI only | [deploy/headless-patch-ci.md](deploy/headless-patch-ci.md) + [external-ci-bridge.md](deploy/external-ci-bridge.md) — gate status without Maker UI |

Procurement packet: this page + [SECURITY.md](../SECURITY.md) + [deploy/helm.md](deploy/helm.md) values table (~8 printed pages).

## Deployment references

- [deploy/README.md](deploy/README.md) — Docker, schema, secrets rotation
- [deploy/helm.md](deploy/helm.md) — production Helm chart (`charts/nimbusware`)
- [deploy/k8s/README.md](deploy/k8s/README.md) — raw reference manifests (verified by `k8s_reference_smoke` workflow dry-run + Helm lint)
- [SECURITY.md](../SECURITY.md) — vulnerability reporting and production checklist
