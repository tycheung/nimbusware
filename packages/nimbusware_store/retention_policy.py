"""Event store retention policy helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from nimbusware_env.settings_resolve import resolve_bool, resolve_int


def event_store_retention_days() -> int | None:
    """Return configured retention window in days, or None when purge is disabled."""
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
    """Truthy ``NIMBUSWARE_EVENT_STORE_LEGAL_HOLD`` blocks purge."""
    return resolve_bool("NIMBUSWARE_EVENT_STORE_LEGAL_HOLD", default=False)


def purge_execute_enabled() -> bool:
    """Requires ``NIMBUSWARE_EVENT_STORE_PURGE_EXECUTE=1`` before DELETE runs."""
    return resolve_bool("NIMBUSWARE_EVENT_STORE_PURGE_EXECUTE", default=False)
