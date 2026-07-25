#!/usr/bin/env python3
"""Live broker HTTP health ping for soak tooling (`sak415-q`).

Curls ``NIMBUSWARE_BROKER_HTTP`` ``/health`` or ``/v1/sak/health`` with a short timeout.

Exit codes:
  0 — health endpoint responded
  1 — URL set but probe failed
  2 — skipped (``NIMBUSWARE_BROKER_HTTP`` unset)
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from typing import Iterable

DEFAULT_TIMEOUT_SEC = 5.0
HEALTH_PATHS = ("/health", "/v1/sak/health")
COMMON_PORTS = (8787, 8080)


def _base_url_from_env() -> str | None:
    raw = os.environ.get("NIMBUSWARE_BROKER_HTTP", "").strip()
    return raw.rstrip("/") if raw else None


def _probe_url(base_url: str, path: str, timeout: float) -> tuple[bool, str]:
    url = f"{base_url}{path}"
    req = urllib.request.Request(url, method="GET")
    token = os.environ.get("NIMBUSWARE_BROKER_TOKEN", "").strip()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300, f"{url} -> HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        return False, f"{url} -> HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{url} -> {exc}"


def probe_health(base_url: str, *, timeout: float = DEFAULT_TIMEOUT_SEC) -> tuple[bool, str]:
    """Try common health paths; return (ok, detail)."""
    last = "no health endpoint responded"
    for path in HEALTH_PATHS:
        ok, detail = _probe_url(base_url, path, timeout)
        if ok:
            return True, detail
        last = detail
    return False, last


def probe_common_ports(host: str = "127.0.0.1", *, timeout: float = DEFAULT_TIMEOUT_SEC) -> tuple[bool, str]:
    """When env URL is unset, try well-known http-admin ports (`sak415-q`)."""
    last = "no broker on common ports"
    for port in COMMON_PORTS:
        base = f"http://{host}:{port}"
        ok, detail = probe_health(base, timeout=timeout)
        if ok:
            return True, detail
        last = detail
    return False, last


def main(argv: Iterable[str] | None = None) -> int:
    _ = argv
    base = _base_url_from_env()
    if not base:
        print("peel_live_ping: skipped (NIMBUSWARE_BROKER_HTTP unset)", file=sys.stderr)
        return 2

    ok, detail = probe_health(base)
    if ok:
        print(f"peel_live_ping: OK — {detail}")
        return 0

    print(f"peel_live_ping: FAIL — {detail}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
