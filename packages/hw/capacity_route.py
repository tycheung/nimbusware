"""Shared dual-run helpers for capacity / hw paths (`sak433-g` / `sak441-c` / `sak490-e`)."""

from __future__ import annotations

from typing import Any, TypeVar

from broker_client.dual_run_route import (
    map_domain_broker_http_miss,
    refuse_when,
)
from broker_client.dual_run_route import (
    require_hit as _require_hit,
)
from broker_client.flags import broker_capacity_enabled, broker_capacity_only

CAPACITY_EXCLUSIVE_MSG = (
    "hw local path unavailable under NIMBUSWARE_BROKER_CAPACITY=1|2; "
    "use SwissArmyNoife HTTP /v1/sak/capacity"
)

CAPACITY_ONLY_MSG = (
    "Nimbusware platform hardware local path unavailable under "
    "NIMBUSWARE_BROKER_CAPACITY=2; use SwissArmyNoife /v1/sak/capacity"
)

T = TypeVar("T")


def capacity_dual_run_on() -> bool:
    return broker_capacity_enabled()


def capacity_broker_only() -> bool:
    return broker_capacity_only()


def refuse_legacy(msg: str | None = None) -> None:
    """Raise when CAPACITY peel is on (``=1|2``) — no local fallthrough."""
    refuse_when(broker_capacity_enabled, msg or CAPACITY_EXCLUSIVE_MSG)


def require_hit(hit: T | None, *, msg: str | None = None) -> T | None:
    return _require_hit(
        hit,
        enabled=broker_capacity_enabled,
        msg=msg or CAPACITY_EXCLUSIVE_MSG,
    )


def map_broker_capacity_http_miss(
    exc: BaseException,
    *,
    feature: str,
    miss_extra: dict[str, Any] | None = None,
    only_msg: str | None = None,
) -> dict[str, Any]:
    """Map capacity peel miss to HTTP body (`sak441-c` / `sak442-b` / `sak490-e` / `sak500-a`).

    Under CAPACITY=2 raise HTTP 503. Under CAPACITY=1 return ``broker_miss`` body.
    When CAPACITY is off, re-raise ``exc``.
    """
    return map_domain_broker_http_miss(  # sak500-a
        exc,
        feature=feature,
        enabled=broker_capacity_enabled,
        only=broker_capacity_only,
        only_code="broker_capacity_only",
        only_msg=only_msg or f"{feature} unavailable under NIMBUSWARE_BROKER_CAPACITY=2: {exc}",
        miss_extra=miss_extra,
        defaults={
            "capacity_source": "broker_miss",
            "fit_via": "broker_miss",
            "profile": {},
            "resource_governor": {},
            "models_ranked": [],
            "models": [],
            "hosts": [],
        },
    )


def map_broker_capacity_http_error(
    exc: BaseException,
    *,
    feature: str,
    only_msg: str | None = None,
) -> None:
    """Raise refuse under CAPACITY=1|2 (non-HTTP callers) (`sak437-d` / `sak442-d`)."""
    raise RuntimeError(
        only_msg or f"{feature} unavailable under NIMBUSWARE_BROKER_CAPACITY=1|2: {exc}"
    ) from exc
