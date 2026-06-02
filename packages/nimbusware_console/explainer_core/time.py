from __future__ import annotations

from datetime import datetime, timezone


def age_seconds_utc(iso: str | None) -> int | None:
    if not isinstance(iso, str):
        return None
    stripped = iso.strip()
    if not stripped:
        return None
    normalised = stripped[:-1] + "+00:00" if stripped.endswith("Z") else stripped
    try:
        parsed = datetime.fromisoformat(normalised)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    age = int((datetime.now(timezone.utc) - parsed).total_seconds())
    if age < 0:
        return None
    return age
