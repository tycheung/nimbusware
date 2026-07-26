from __future__ import annotations

from typing import Any

from broker_client.dual_run_route import map_domain_broker_http_miss, refuse_when
from broker_client.flags import broker_egress_enabled, broker_egress_only

EGRESS_EXCLUSIVE_MSG = (
    "executor egress local path unavailable under NIMBUSWARE_BROKER_EGRESS=1|2; "
    "use SwissArmyNoife egress_check"
)

EGRESS_ONLY_MSG = (
    "Nimbusware egress local path unavailable under "
    "NIMBUSWARE_BROKER_EGRESS=2; use SwissArmyNoife egress_check"
)


def refuse_legacy(msg: str | None = None) -> None:
    """Raise when EGRESS peel is on (``=1|2``) — no local fallthrough."""
    refuse_when(broker_egress_enabled, msg or EGRESS_EXCLUSIVE_MSG)


def raise_egress_peel_miss(feature: str = "egress") -> None:
    """Raise structured broker miss for EGRESS peel (`sak496-d` / sak416-i)."""
    raise RuntimeError(
        f"broker_miss: {feature}: unavailable under NIMBUSWARE_BROKER_EGRESS=1|2; "
        "executor local egress removed (sak416-i)"
    )


def map_broker_egress_http_miss(
    exc: BaseException,
    *,
    feature: str,
    miss_extra: dict[str, Any] | None = None,
    only_msg: str | None = None,
) -> dict[str, Any]:
    """Map egress peel miss to HTTP body (`sak496-d` / `sak499-f`).

    Under EGRESS=2 raise HTTP 503. Under EGRESS=1 return ``broker_miss`` body.
    When EGRESS is off, re-raise ``exc``.
    """
    return map_domain_broker_http_miss(  # sak499-f
        exc,
        feature=feature,
        enabled=broker_egress_enabled,
        only=broker_egress_only,
        only_code="broker_egress_only",
        only_msg=only_msg or f"{feature} unavailable under NIMBUSWARE_BROKER_EGRESS=2: {exc}",
        miss_extra=miss_extra,
    )
