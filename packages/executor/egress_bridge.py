from __future__ import annotations

from uuid import UUID

from broker_client.flags import broker_egress_enabled, broker_egress_only
from broker_client.stage_bind import egress_check_via_broker


def try_broker_egress_check(url: str) -> dict | None:
    """Return broker egress check result when enabled; dual-run falls back with ``None``.

    Broker-only (``=2``): re-raise on failure (no local egress fallback).
    """
    if not broker_egress_enabled():
        return None
    try:
        return egress_check_via_broker(url)
    except Exception:
        if broker_egress_only():
            raise
        return None


def host_matches_allowlist(host: str, domain_allowlist: list[str]) -> bool:
    """Local allowlist removed (sak416-i); use broker ``egress_check``."""
    raise RuntimeError(
        "executor.egress local allowlist removed (sak416-i); use try_broker_egress_check"
    )


def assert_egress_allowed(
    *,
    actor_role_id: UUID,
    target_host: str,
    scraper_role_allowlist: list[UUID],
    domain_allowlist: list[str],
) -> None:
    """Local egress assert removed (sak416-i); use broker ``egress_check``."""
    _ = (actor_role_id, target_host, scraper_role_allowlist, domain_allowlist)
    raise RuntimeError(
        "executor.egress local policy removed (sak416-i); use try_broker_egress_check"
    )


__all__ = [
    "assert_egress_allowed",
    "host_matches_allowlist",
    "try_broker_egress_check",
]
