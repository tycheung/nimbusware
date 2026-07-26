from __future__ import annotations

from urllib.parse import urlparse
from uuid import UUID

import httpx


class EgressResponseTooLarge(Exception):
    """Declared ``Content-Length`` or streamed body exceeds ``max_response_bytes``."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _host_matches_allowlist(host: str, domain_allowlist: list[str]) -> bool:
    host_l = host.lower()
    for raw in domain_allowlist:
        item = str(raw or "").strip().lower()
        if not item:
            continue
        if item.startswith("."):
            if host_l == item[1:] or host_l.endswith(item):
                return True
        elif host_l == item:
            return True
    return False


def _local_egress_allowed(
    *,
    actor_role_id: UUID,
    host: str,
    scraper_role_allowlist: list[UUID],
    domain_allowlist: list[str],
) -> None:
    if scraper_role_allowlist and actor_role_id not in scraper_role_allowlist:
        msg = f"actor {actor_role_id} not in scraper_role_allowlist"
        raise PermissionError(msg)
    if domain_allowlist and not _host_matches_allowlist(host, domain_allowlist):
        msg = f"host {host!r} not in domain_allowlist"
        raise PermissionError(msg)


def _apply_broker_egress_check(
    url: str,
    *,
    actor_role_id: UUID,
    host: str,
    scraper_role_allowlist: list[UUID],
    domain_allowlist: list[str],
) -> None:
    """Broker egress when EGRESS peel is on; otherwise enforce frozen run allowlists."""
    from broker_client.flags import broker_egress_enabled
    from executor.egress_bridge import try_broker_egress_check

    if not broker_egress_enabled():
        _local_egress_allowed(
            actor_role_id=actor_role_id,
            host=host,
            scraper_role_allowlist=scraper_role_allowlist,
            domain_allowlist=domain_allowlist,
        )
        return

    hit = try_broker_egress_check(url)
    if hit is None:
        # sak416-i / sak494-e / sak496-d: peel on + no broker hit — refuse local fallthrough.
        # raise_egress_peel_miss → RuntimeError("broker_miss: egress: ... local egress removed")
        from executor.broker_route import raise_egress_peel_miss

        raise_egress_peel_miss("egress")
    if hit.get("allowed") is False or hit.get("ok") is False:
        msg = hit.get("reason") or hit.get("message") or f"broker egress denied for {url!r}"
        raise PermissionError(msg)


def egress_checked_httpx_get(
    url: str,
    *,
    actor_role_id: UUID,
    scraper_role_allowlist: list[UUID],
    domain_allowlist: list[str],
    timeout_seconds: float = 30.0,
    client: httpx.Client | None = None,
    max_response_bytes: int | None = None,
) -> httpx.Response:
    """``GET`` ``url`` after egress policy (broker when EGRESS peel on, else local allowlists)."""
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        msg = "URL has no hostname for egress check"
        raise ValueError(msg)
    _apply_broker_egress_check(
        url,
        actor_role_id=actor_role_id,
        host=host,
        scraper_role_allowlist=scraper_role_allowlist,
        domain_allowlist=domain_allowlist,
    )
    c = client or httpx.Client()
    if max_response_bytes is None:
        return c.get(url, timeout=timeout_seconds)
    cap = max_response_bytes
    with c.stream("GET", url, timeout=timeout_seconds) as resp:
        resp.raise_for_status()
        req = resp.request
        cl_header = resp.headers.get("content-length")
        if cl_header is not None:
            try:
                cl_int = int(cl_header)
            except ValueError:
                pass
            else:
                if cl_int > cap:
                    msg = f"Content-Length {cl_int} exceeds max_response_bytes={cap}"
                    raise EgressResponseTooLarge(msg)
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_bytes():
            total += len(chunk)
            if total > cap:
                msg = f"response body length {total} exceeds max_response_bytes={cap}"
                raise EgressResponseTooLarge(msg)
            chunks.append(chunk)
        content = b"".join(chunks)
        return httpx.Response(
            resp.status_code,
            headers=resp.headers,
            content=content,
            request=req,
        )
