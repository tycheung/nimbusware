# Product editions

| Edition | Install | Scope |
|---------|---------|--------|
| **Individual** (default) | `python scripts/install_nimbusware.py` | Single operator, repo-scoped memory, no IAM |
| **Enterprise** | `python scripts/install_nimbusware.py --edition enterprise` | Multi-tenant IAM, fleet memory, config NOTIFY, Redis workers, fleet SLI |

Set `NIMBUSWARE_EDITION=individual|enterprise` in `.env`. Enterprise-only routes return **404** on Individual. Check: `GET /v1/platform/edition`.

## Enterprise capabilities

- **IAM** — API keys, tenants, row-level isolation (`X-Nimbusware-Api-Key`)
- **Fleet memory** — org-scoped index, canonical store sync (`nimbusware-memory-sync`)
- **Config NOTIFY** — Postgres `LISTEN/NOTIFY` + cache invalidation
- **Object-store primary** — S3-compatible scraper artifact backend
- **Redis fleet worker** — shared verify queue, health/back-pressure metrics
- **Fleet Ollama SLI** — sustained health p95 export + preflight aggregate API
- **Admin Fleet tab** — `/v1/admin/app/fleet` (tenant switcher, fleet memory, Ollama SLI, worker health, hardware tiers, cross-tenant gate comparison)

## Auth scopes (Enterprise)

| Scope | Use |
|-------|-----|
| `maker_user` | Maker app / user routes only |
| `maker_admin` | Admin Console + control-plane mutations (includes `maker_user`) |

Bootstrap (`POST /v1/enterprise/iam/bootstrap`) returns a **maker_admin** key. Create tenant user keys with `POST /v1/enterprise/tenants/{id}/api-keys` and `"api_scopes": ["maker_user"]`.

## User vs Admin surfaces

| Surface | Who | Auth |
|---------|-----|------|
| **Maker** (default) | End user / maker | No admin token for the product loop |
| **Admin Console** | Ops / dev / admin | Admin token at sign-in; API uses `X-Nimbusware-Admin-Token` (Individual) or `maker_admin` API key (Enterprise) |
| **Maker → Admin** | Admin on same machine | Maker shell links to `/v1/admin/app/` |

Enterprise APIs: `GET /v1/enterprise/fleet/analytics/compare`, `GET /v1/enterprise/fleet-learnings/search`, `GET /v1/enterprise/audit-export`, `GET /v1/enterprise/research-index`. See [enterprise-buyer.md](../enterprise-buyer.md).

External chat webhook: [integrations-external-chat.md](../integrations-external-chat.md).
