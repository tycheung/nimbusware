"""Network egress allowlists from frozen policy snapshot (plan §6.3A, §9.1)."""

from __future__ import annotations

from ipaddress import ip_address
from uuid import UUID


def host_matches_allowlist(host: str, domain_allowlist: list[str]) -> bool:
    """Hostname suffix rules for ASCII/punycode; exact match for IP literals (plan §6.3A)."""
    h = host.strip().lower()
    try:
        ip_address(h)
        return h in {x.strip().lower() for x in domain_allowlist}
    except ValueError:
        pass
    for entry in domain_allowlist:
        e = entry.strip().lower()
        if not e:
            continue
        if e.startswith("."):
            if h == e[1:] or h.endswith(e):
                return True
        elif h == e:
            return True
    return False


def assert_egress_allowed(
    *,
    actor_role_id: UUID,
    target_host: str,
    scraper_role_allowlist: list[UUID],
    domain_allowlist: list[str],
) -> None:
    if actor_role_id not in scraper_role_allowlist:
        msg = f"role {actor_role_id} not in scraper_role_allowlist"
        raise PermissionError(msg)
    if not host_matches_allowlist(target_host, domain_allowlist):
        msg = f"host {target_host!r} not in domain_allowlist"
        raise PermissionError(msg)
