from __future__ import annotations

from typing import Any

from broker_client.dual_run_route import map_domain_broker_http_miss, refuse_when
from broker_client.flags import broker_research_enabled, broker_research_only

RESEARCH_EXCLUSIVE_MSG = (
    "research local path unavailable under NIMBUSWARE_BROKER_RESEARCH=1|2; "
    "use SwissArmyNoife research_fetch"
)

RESEARCH_ONLY_MSG = (
    "Nimbusware research local path unavailable under "
    "NIMBUSWARE_BROKER_RESEARCH=2; use SwissArmyNoife research_fetch"
)


def refuse_legacy(msg: str | None = None) -> None:
    """Raise when RESEARCH peel is on (``=1|2``) — no local fallthrough."""
    refuse_when(broker_research_enabled, msg or RESEARCH_EXCLUSIVE_MSG)


def raise_research_peel_miss(feature: str = "research_fetch") -> None:
    """Raise structured broker miss when RESEARCH peel is on (`sak496-d`)."""
    if broker_research_enabled():
        raise RuntimeError(
            f"broker_miss: {feature}: unavailable under NIMBUSWARE_BROKER_RESEARCH=1|2"
        )


def map_broker_research_http_miss(
    exc: BaseException,
    *,
    feature: str,
    miss_extra: dict[str, Any] | None = None,
    only_msg: str | None = None,
) -> dict[str, Any]:
    """Map research peel miss to HTTP body (`sak496-d` / `sak499-f`).

    Under RESEARCH=2 raise HTTP 503. Under RESEARCH=1 return ``broker_miss`` body.
    When RESEARCH is off, re-raise ``exc``.
    """
    return map_domain_broker_http_miss(  # sak499-f
        exc,
        feature=feature,
        enabled=broker_research_enabled,
        only=broker_research_only,
        only_code="broker_research_only",
        only_msg=only_msg or f"{feature} unavailable under NIMBUSWARE_BROKER_RESEARCH=2: {exc}",
        miss_extra=miss_extra,
    )
