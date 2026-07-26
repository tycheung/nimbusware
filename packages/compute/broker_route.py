"""Shared HTTP dual-run helpers for compute routes (`sak431-f` / `sak434-d` / `sak490-e`).

Avoids importing ``api`` package root (which loads the FastAPI app).
Primitives live in ``broker_client.dual_run_route``; this module adds HTTP miss shapes.
"""

from __future__ import annotations

from typing import Any

from broker_client.dual_run_route import (
    broker_problem,
    map_domain_broker_http_miss,
    refuse_when,
)
from broker_client.dual_run_route import (
    refuse_broker_only_http as _refuse_broker_only_http,
)
from broker_client.flags import broker_compute_enabled, broker_compute_only
from compute.broker_miss import broker_miss

COMPUTE_ONLY_MSG = (
    "Nimbusware /v1/compute/* local mesh unavailable under "
    "NIMBUSWARE_BROKER_COMPUTE=2; use SwissArmyNoife /v1/sak/compute/*"
)

COMPUTE_EXCLUSIVE_MSG = (
    "Nimbusware local compute mesh unavailable under NIMBUSWARE_BROKER_COMPUTE=1|2; "
    "use SwissArmyNoife compute_work / compute_node"
)

# Back-compat alias for SSE/export imports (`sak490-e`).
_problem = broker_problem


def refuse_broker_only_http() -> None:
    """Raise 503 when COMPUTE=2 (broker-only)."""
    _refuse_broker_only_http(
        only=broker_compute_only,
        code="broker_compute_only",
        message=COMPUTE_ONLY_MSG,
    )


def refuse_compute_exclusive(msg: str | None = None) -> None:
    """Raise when COMPUTE peel is on (``=1|2``) — shared with dual_run_route (`sak434-d`)."""
    refuse_when(broker_compute_enabled, msg or COMPUTE_EXCLUSIVE_MSG)


def miss(error: str, **extra: Any) -> dict[str, Any]:
    """Standard COMPUTE=1 broker miss (no local fallback)."""
    payload = dict(extra) if extra else None
    return broker_miss(error=error, extra=payload)


def map_broker_compute_http_error(
    exc: BaseException,
    *,
    feature: str,
    only_msg: str | None = None,
    miss_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map broker failure to HTTP 503 under COMPUTE=2, else ``broker_miss`` dict (`sak436-c` / `sak499-f`).

    Callers under COMPUTE=1 return the dict as HTTP 200 (observability, no local mesh).
    """
    return map_domain_broker_http_miss(  # sak499-f
        exc,
        feature=feature,
        only=broker_compute_only,
        only_code="broker_compute_only",
        only_msg=only_msg or f"{feature} unavailable under NIMBUSWARE_BROKER_COMPUTE=2: {exc}",
        miss_extra=miss_extra,
        defaults={"node": None},
    )


def map_broker_chat_compute_miss(
    error: str,
    *,
    feature: str,
    only_msg: str | None = None,
    miss_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Chat delegate/opt-in miss helper (`sak437-c` / `sak499-f`) — =2 → 503, else ``broker_miss``."""
    return map_domain_broker_http_miss(  # sak499-f
        error,
        feature=feature,
        only=broker_compute_only,
        only_code="broker_compute_only",
        only_msg=only_msg or f"{feature} unavailable under NIMBUSWARE_BROKER_COMPUTE=2: {error}",
        miss_extra=miss_extra,
        defaults={"node": None},
    )


def compute_dual_run_on() -> bool:
    return broker_compute_enabled()


def compute_broker_only() -> bool:
    return broker_compute_only()
