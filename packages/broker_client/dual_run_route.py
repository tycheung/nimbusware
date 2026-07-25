"""Shared dual-run refuse helpers for compute + capacity peels (`sak434-d` / `sak494-j` / `sak499-f`).

Domain packages keep thin facades (``compute.broker_route``, ``hw.capacity_route``,
``memory.broker_route``, ``research.broker_route``, ``executor.broker_route``,
``agent_tools.broker_route``) that wrap these primitives with domain-specific messages
and HTTP miss shapes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def build_domain_peel_miss(
    error: str,
    *,
    feature: str,
    miss_extra: dict[str, Any] | None = None,
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Degraded peel miss envelope for domain HTTP routes (`sak494-j`).

    Wraps ``peel_assert.build_http_miss`` so memory/capacity routes share one builder.
    """
    from broker_client.peel_assert import build_http_miss

    merged: dict[str, Any] = dict(defaults or {})
    if miss_extra:
        merged.update(miss_extra)
    return build_http_miss(
        error,
        feature=feature,
        status="degraded",
        miss_extra=merged or None,
    )


def map_domain_broker_http_miss(
    err: BaseException | str,
    *,
    feature: str,
    only: Callable[[], bool],
    only_code: str,
    only_msg: str | None = None,
    enabled: Callable[[], bool] | None = None,
    miss_extra: dict[str, Any] | None = None,
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Domain peel HTTP miss: ``build_domain_peel_miss`` + ``map_broker_http_miss`` (`sak499-f`)."""

    def _build_miss(error: str) -> dict[str, Any]:
        return build_domain_peel_miss(
            error,
            feature=feature,
            miss_extra=miss_extra,
            defaults=defaults,
        )

    msg = only_msg or f"{feature} unavailable under peel=2: {err}"
    return map_broker_http_miss(
        err,
        enabled=enabled,
        only=only,
        only_code=only_code,
        only_msg=msg,
        build_miss=_build_miss,
    )


def broker_problem(code: str, message: str) -> dict[str, str]:
    """RFC7807-style problem payload for broker-only HTTP 503 (`sak490-e`)."""
    return {"code": code, "message": message}


def refuse_broker_only_http(
    *,
    only: Callable[[], bool],
    code: str,
    message: str,
) -> None:
    """Raise HTTP 503 when peel flag is broker-only (``=2``)."""
    if only():
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail=broker_problem(code, message),
        )


def map_broker_http_miss(
    err: BaseException | str,
    *,
    enabled: Callable[[], bool] | None = None,
    only: Callable[[], bool],
    only_code: str,
    only_msg: str,
    build_miss: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    """Map peel miss: ``=2`` → HTTP 503 problem; ``=1`` → miss dict via ``build_miss``.

    When ``enabled`` is set and false, re-raise ``err`` if it is an exception.
    When ``enabled`` is omitted, assume the caller already gated on peel enabled.
    """
    if enabled is not None and not enabled():
        if isinstance(err, BaseException):
            raise err
        raise RuntimeError(str(err))

    if only():
        from fastapi import HTTPException

        exc = err if isinstance(err, BaseException) else None
        raise HTTPException(
            status_code=503,
            detail=broker_problem(only_code, only_msg),
        ) from exc

    error = str(err) if isinstance(err, BaseException) else err
    return build_miss(error)


def refuse_when(enabled: Callable[[], bool], msg: str) -> None:
    """Raise ``RuntimeError(msg)`` when ``enabled()`` is true."""
    if enabled():
        raise RuntimeError(msg)


def require_hit(
    hit: T | None,
    *,
    enabled: Callable[[], bool],
    msg: str,
) -> T | None:
    if hit is not None:
        return hit
    refuse_when(enabled, msg)
    return None


def try_or_refuse(
    fn: Callable[[], T],
    *,
    enabled: Callable[[], bool],
    broker_only: Callable[[], bool],
    msg: str,
) -> T | None:
    try:
        return fn()
    except Exception as exc:
        if broker_only():
            raise
        if enabled():
            raise RuntimeError(msg) from exc
        return None
