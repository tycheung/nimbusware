from __future__ import annotations

from typing import Any


def broker_miss(
    *,
    error: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Standard shape when COMPUTE=1 broker path misses (no local fallback)."""
    out: dict[str, Any] = {"via": "broker_miss", "error": error, "node": None}
    if extra:
        out.update(extra)
    return out
