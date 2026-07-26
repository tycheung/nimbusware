from __future__ import annotations

from typing import Any

from broker_client.dual_run_route import map_domain_broker_http_miss, refuse_when
from broker_client.flags import broker_memory_enabled, broker_memory_only
from memory.peel_factory import build_memory_chunk_store

MEMORY_ONLY_MSG = (
    "Nimbusware fleet-memory local path unavailable under "
    "NIMBUSWARE_BROKER_MEMORY=2; use SwissArmyNoife memory_search"
)

MEMORY_EXCLUSIVE_MSG = (
    "fleet memory unavailable under NIMBUSWARE_BROKER_MEMORY=1|2; use SwissArmyNoife memory_search"
)

STATUS_PROBE_QUERY = "fleet-memory-status-probe"


def refuse_legacy(msg: str | None = None) -> None:
    """Raise when MEMORY peel is on (``=1|2``) — no local fallthrough (`sak494-a` / `sak495-a`)."""
    refuse_when(broker_memory_enabled, msg or MEMORY_EXCLUSIVE_MSG)


def broker_memory_hits(broker_result: dict[str, Any]) -> list[dict[str, Any]]:
    hits_raw = broker_result.get("hits") or broker_result.get("results") or []
    if not isinstance(hits_raw, list):
        return []
    out: list[dict[str, Any]] = []
    for hit in hits_raw:
        if isinstance(hit, dict):
            out.append(hit)
        else:
            out.append({"text": str(hit)})
    return out


def format_broker_memory_excerpt(hits: list[dict[str, Any]], *, max_chars: int) -> str | None:
    if max_chars <= 0:
        return None
    parts: list[str] = []
    for i, hit in enumerate(hits, start=1):
        excerpt = hit.get("excerpt") or hit.get("text") or hit.get("body") or str(hit)
        cid = hit.get("chunk_id") or hit.get("id") or "?"
        score = hit.get("score")
        if score is not None:
            block = f"[{i}] chunk={cid} score={score}\n{excerpt}"
        else:
            block = f"[{i}] chunk={cid}\n{excerpt}"
        parts.append(block)
    if not parts:
        return None
    body = "\n\n".join(parts)
    if len(body) > max_chars:
        return body[: max_chars - 3] + "..."
    return body


def require_local_memory_chunk_store(
    *,
    feature: str,
    miss_extra: dict[str, Any] | None = None,
    allow_in_memory: bool = True,
) -> Any:
    """Guard ``build_memory_chunk_store`` under MEMORY peel (`sak498-b`).

    Returns peel-miss dict under MEMORY=1; raises HTTP 503 under MEMORY=2;
    otherwise returns the local chunk store (possibly ``None``).
    """
    if broker_memory_enabled():
        return map_broker_memory_local_refuse(feature=feature, miss_extra=miss_extra)
    return build_memory_chunk_store(allow_in_memory=allow_in_memory)


MEMORY_STORE_UNAVAILABLE = "memory_store_unavailable"


def resolve_memory_store_or_miss(
    *,
    feature: str,
    miss_extra: dict[str, Any] | None = None,
    allow_in_memory: bool = True,
    unavailable_msg: str = "memory chunk store is not configured",
    local_only: bool = False,
    allow_none: bool = False,
) -> Any | dict[str, Any] | None:
    """Resolve local memory chunk store or peel miss (`sak498-h`).

    Unless ``local_only``, applies MEMORY peel guard via ``require_local_memory_chunk_store``.
    Raises HTTP 503 when the store is missing unless ``allow_none``.
    """
    if local_only:
        store = build_memory_chunk_store(allow_in_memory=allow_in_memory)
    else:
        store = require_local_memory_chunk_store(
            feature=feature,
            miss_extra=miss_extra,
            allow_in_memory=allow_in_memory,
        )
        if isinstance(store, dict):
            return store
    if store is None:
        if allow_none:
            return None
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail={
                "code": MEMORY_STORE_UNAVAILABLE,
                "message": unavailable_msg,
            },
        )
    return store


def map_broker_memory_local_refuse(
    *,
    feature: str,
    miss_extra: dict[str, Any] | None = None,
    msg: str | None = None,
) -> dict[str, Any]:
    """Refuse local fleet-memory peel_index under MEMORY=1|2 (`sak494-b`)."""
    error_msg = msg or (
        f"{feature} unavailable under NIMBUSWARE_BROKER_MEMORY=1|2; use SwissArmyNoife memory_index"
    )
    return map_broker_memory_http_miss(
        RuntimeError(error_msg),
        feature=feature,
        miss_extra=miss_extra,
        only_msg=MEMORY_ONLY_MSG,
    )


def map_broker_memory_http_miss(
    exc: BaseException,
    *,
    feature: str,
    miss_extra: dict[str, Any] | None = None,
    only_msg: str | None = None,
) -> dict[str, Any]:
    """Map memory peel miss to HTTP body (`sak493-i` / `sak499-f`).

    Under MEMORY=2 raise HTTP 503. Under MEMORY=1 return ``broker_miss`` body.
    When MEMORY is off, re-raise ``exc``.
    """
    return map_domain_broker_http_miss(  # sak499-f
        exc,
        feature=feature,
        enabled=broker_memory_enabled,
        only=broker_memory_only,
        only_code="broker_memory_only",
        only_msg=only_msg or f"{feature} unavailable under NIMBUSWARE_BROKER_MEMORY=2: {exc}",
        miss_extra=miss_extra,
    )
