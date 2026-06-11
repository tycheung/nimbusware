from __future__ import annotations

from urllib.parse import urlparse
from uuid import UUID

import httpx

from nimbusware_executor.egress import assert_egress_allowed


class EgressResponseTooLarge(Exception):
    """Declared ``Content-Length`` or streamed body exceeds ``max_response_bytes``."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


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
    """``GET`` ``url`` after ``assert_egress_allowed`` on the request host."""
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        msg = "URL has no hostname for egress check"
        raise ValueError(msg)
    assert_egress_allowed(
        actor_role_id=actor_role_id,
        target_host=host,
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
