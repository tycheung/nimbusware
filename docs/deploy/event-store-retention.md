# Event store retention (§6.6)

Nimbusware run events live in Postgres `event_store` (or in-memory for quick mode). This document describes retention policy **without** implementing automated purge — that job is deferred until operators request it.

## Append-only invariant

Production schema installs `prevent_event_store_mutation()` triggers that reject `UPDATE` and `DELETE` on `event_store`. Verified by `tests/integration/test_event_store_append_only.py`. Audit timelines remain tamper-evident.

## Retention vs export window

| Mechanism | Scope | Default |
|-----------|--------|---------|
| `NIMBUSWARE_AUDIT_RETENTION_DAYS` | Enterprise audit **export** window (`GET /v1/runs/{id}/audit-export`) | 90 days |
| `NIMBUSWARE_EVENT_STORE_RETENTION_DAYS` | Planned **purge** horizon for raw rows (not active until purge job ships) | 0 (disabled) |

Setting `NIMBUSWARE_EVENT_STORE_RETENTION_DAYS` documents operator intent only. `nimbusware_store.retention_policy.event_store_retention_days()` returns `None` when unset or zero.

## PII and redaction

Before sharing audit bundles outside the tenant boundary, redact or omit:

- `metadata` keys that carry operator prompts, API keys, or filesystem paths outside the project workspace
- `payload` fields from chat or interjection events when exporting for support tickets
- Scraper artifact URLs that embed credentials

Legal hold and IAM-scoped retention deferrals remain Enterprise Lane D work.

## Future purge job (sketch)

When implemented, a scheduled job will:

1. Read `event_store_retention_days()`; skip when `None`
2. Delete rows older than the window **only** when legal hold is absent
3. Emit `event_store.retention.purged` metrics for Admin fleet monitoring

Until then, size Postgres with standard volume management and rely on audit export for compliance extracts.

See also: [packages/nimbusware_store/README.md](../../packages/nimbusware_store/README.md), [enterprise-buyer.md](../enterprise-buyer.md).
