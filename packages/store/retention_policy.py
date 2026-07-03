from __future__ import annotations

from datetime import datetime, timedelta, timezone

from env.settings_resolve import resolve_bool, resolve_int


def event_store_retention_days() -> int | None:
    raw = resolve_int("NIMBUSWARE_EVENT_STORE_RETENTION_DAYS", default=0)
    if raw <= 0:
        return None
    return max(1, min(3650, raw))


def purge_eligible_before(*, now: datetime | None = None) -> datetime | None:
    days = event_store_retention_days()
    if days is None:
        return None
    anchor = now or datetime.now(timezone.utc)
    return anchor - timedelta(days=days)


def legal_hold_enabled() -> bool:
    return resolve_bool("NIMBUSWARE_EVENT_STORE_LEGAL_HOLD", default=False)


def tenant_legal_hold_enabled(tenant_slug: str = "default") -> bool:
    if legal_hold_enabled():
        return True
    from config.tenant_policy_store import load_tenant_audit_policy

    return bool(load_tenant_audit_policy(tenant_slug).get("legal_hold"))


def purge_blocked_by_legal_hold(tenant_slug: str = "default") -> bool:
    return tenant_legal_hold_enabled(tenant_slug)


def purge_execute_enabled() -> bool:
    return resolve_bool("NIMBUSWARE_EVENT_STORE_PURGE_EXECUTE", default=False)
