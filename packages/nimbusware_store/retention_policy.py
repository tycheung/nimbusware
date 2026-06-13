"""Event store retention policy helpers (document-only until purge job ships)."""

from __future__ import annotations

from nimbusware_env.settings_resolve import resolve_int


def event_store_retention_days() -> int | None:
    """Return configured retention window in days, or None when purge is disabled."""
    raw = resolve_int("NIMBUSWARE_EVENT_STORE_RETENTION_DAYS", default=0)
    if raw <= 0:
        return None
    return max(1, min(3650, raw))
