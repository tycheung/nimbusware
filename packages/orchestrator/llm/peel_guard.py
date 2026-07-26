from __future__ import annotations

import httpx


def _llm_broker_miss_or_transport(exc: BaseException) -> bool:  # sak499-e
    if isinstance(exc, httpx.HTTPError):
        return True
    msg = str(exc).lower()
    return "broker_miss" in msg or "broker miss" in msg or "transport" in msg
