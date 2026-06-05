# Enterprise research index and egress audit

Enterprise edition maintains tenant-scoped JSONL ledgers under `.nimbusware/enterprise/{tenant_id}/` on the repo root (`NIMBUSWARE_REPO_ROOT`).

## Ledgers

| File | Written by | Purpose |
|------|------------|---------|
| `research_index.jsonl` | `append_enterprise_research_index` after `research.pattern.indexed` | Tenant pattern catalog for cross-run search |
| `egress_audit.jsonl` | Executor egress hooks (append-only) | Allow/deny audit for compliance export |

## API (`X-Nimbusware-Api-Key`, Enterprise edition)

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/v1/enterprise/research-index?limit=500` | `{ tenant_id, rows[], count }` |
| `GET` | `/v1/enterprise/egress-audit?format=json` | `{ rows[], count }` |
| `GET` | `/v1/enterprise/egress-audit?format=jsonl` | NDJSON download |

Bundled with fleet IAM audit via `GET /v1/enterprise/audit-export` (see [enterprise-buyer.md](enterprise-buyer.md)).
