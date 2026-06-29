# Event store retention (§6.6)

Nimbusware run events live in Postgres `event_store` (or in-memory for quick mode). Retention policy, legal hold, and an optional purge execute path are documented below.

## Append-only invariant

Production schema installs `prevent_event_store_mutation()` triggers that reject `UPDATE` and `DELETE` on `event_store`. Verified by `tests/integration/test_event_store_append_only.py`. Audit timelines remain tamper-evident.

## Retention vs export window

| Mechanism | Scope | Default |
|-----------|--------|---------|
| `NIMBUSWARE_AUDIT_RETENTION_DAYS` | Enterprise audit **export** window (`GET /v1/runs/{id}/audit-export`) | 90 days |
| `NIMBUSWARE_EVENT_STORE_RETENTION_DAYS` | Purge horizon for raw rows; dry-run count when set | 0 (disabled) |

Setting `NIMBUSWARE_EVENT_STORE_RETENTION_DAYS` documents operator intent only. `nimbusware_store.retention_policy.event_store_retention_days()` returns `None` when unset or zero.

## PII and redaction

Before sharing audit bundles outside the tenant boundary, redact or omit:

- `metadata` keys that carry operator prompts, API keys, or filesystem paths outside the project workspace
- `payload` fields from chat or interjection events when exporting for support tickets
- Scraper artifact URLs that embed credentials

Legal hold blocks purge via `NIMBUSWARE_EVENT_STORE_LEGAL_HOLD` or tenant `audit-policy.legal_hold` (Admin Fleet toggle; `GET/PUT /v1/enterprise/audit-policy`). IAM-scoped deferrals remain Enterprise Lane D work.

## Purge helper

`scripts/database/purge_event_store_retention.py` reports eligible row counts (dry-run by default).

| Env | Effect |
|-----|--------|
| `NIMBUSWARE_EVENT_STORE_RETENTION_DAYS` | Retention window; `0` or unset disables purge reporting |
| `NIMBUSWARE_EVENT_STORE_LEGAL_HOLD` | Truthy blocks purge (script exits before counting or deleting) |
| Tenant `audit-policy.legal_hold` | When Postgres config is enabled, Fleet legal-hold toggle blocks purge for that tenant |
| `NIMBUSWARE_EVENT_STORE_PURGE_EXECUTE` | Must be `1` for `--execute` to run `DELETE` via `nimbusware_store.purge.purge_events_before` |

Append-only triggers on `event_store` still reject `DELETE` until an operator removes or bypasses `prevent_event_store_mutation()`.

```bash
python scripts/database/purge_event_store_retention.py              # dry-run count
NIMBUSWARE_EVENT_STORE_PURGE_EXECUTE=1 \
  python scripts/database/purge_event_store_retention.py --execute  # requires trigger override
```

Reference manifest: `docs/deploy/k8s/event-store-purge-cronjob.yaml` (suspended). Helm: enable when `hardening.eventStorePurge` is set.

See also: [packages/nimbusware_store/README.md](../../packages/nimbusware_store/README.md), [enterprise-buyer.md](../enterprise-buyer.md).
