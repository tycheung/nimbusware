from __future__ import annotations

from urllib.parse import urlparse
from uuid import UUID

import httpx


class EgressResponseTooLarge(Exception):
    """Declared ``Content-Length`` or streamed body exceeds ``max_response_bytes``."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _apply_broker_egress_check(url: str) -> None:
    """Require broker egress decision (local policy removed sak416-i)."""
    from executor.broker_route import raise_egress_peel_miss
    from executor.egress_bridge import try_broker_egress_check

    hit = try_broker_egress_check(url)
    if hit is None:
        raise_egress_peel_miss("egress")  # sak494-e / sak496-d: broker_miss: egress
        raise RuntimeError(
            "executor local egress removed (sak416-i); set NIMBUSWARE_BROKER_EGRESS=1|2"
        )
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
    """``GET`` ``url`` after broker egress policy (local allowlist removed)."""
    _ = (actor_role_id, scraper_role_allowlist, domain_allowlist)
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        msg = "URL has no hostname for egress check"
        raise ValueError(msg)
    _apply_broker_egress_check(url)
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
