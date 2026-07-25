from __future__ import annotations

from typing import Any

from broker_client.flags import broker_research_enabled, broker_research_only
from broker_client.stage_bind import research_fetch_via_broker


def try_broker_research_fetch(url: str, **kwargs: Any) -> dict | None:
    """Return broker research fetch result when enabled; dual-run falls back with ``None``.

    Broker-only (``=2``): re-raise on failure (no local research fallback).
    """
    if not broker_research_enabled():
        return None
    try:
        return research_fetch_via_broker(url, **kwargs)
    except Exception:
        if broker_research_only():
            raise
        return None
