from __future__ import annotations

from typing import Any

from broker_client.dual_run_route import map_domain_broker_http_miss, refuse_when
from broker_client.flags import (
    broker_sandbox_enabled,
    broker_sandbox_only,
    broker_tools_enabled,
    broker_tools_only,
)

SANDBOX_EXCLUSIVE_MSG = (
    "agent_tools sandbox local path unavailable under NIMBUSWARE_BROKER_SANDBOX=1|2; "
    "use SwissArmyNoife sandbox_exec"
)

SANDBOX_ONLY_MSG = (
    "Nimbusware sandbox local path unavailable under "
    "NIMBUSWARE_BROKER_SANDBOX=2; use SwissArmyNoife sandbox_exec"
)

TOOLS_EXCLUSIVE_MSG = (
    "agent_tools shell local path unavailable under NIMBUSWARE_BROKER_TOOLS=1|2; "
    "use SwissArmyNoife shell_exec"
)

TOOLS_ONLY_MSG = (
    "Nimbusware tools local path unavailable under "
    "NIMBUSWARE_BROKER_TOOLS=2; use SwissArmyNoife shell_exec"
)


def raise_sandbox_peel_miss(feature: str = "shell") -> None:
    """Raise structured broker miss when SANDBOX peel is on (`sak496-d`)."""
    if broker_sandbox_enabled():
        raise RuntimeError(
            f"broker_miss: {feature}: sandbox unavailable under NIMBUSWARE_BROKER_SANDBOX=1|2"
        )


def raise_tools_peel_miss(feature: str = "shell") -> None:
    """Raise structured broker miss when TOOLS peel is on (`sak496-d`)."""
    if broker_tools_enabled():
        raise RuntimeError(
            f"broker_miss: {feature}: tools unavailable under NIMBUSWARE_BROKER_TOOLS=1|2"
        )


def refuse_sandbox_legacy(msg: str | None = None) -> None:
    """Raise when SANDBOX peel is on (``=1|2``) — no local fallthrough."""
    refuse_when(broker_sandbox_enabled, msg or SANDBOX_EXCLUSIVE_MSG)


def refuse_tools_legacy(msg: str | None = None) -> None:
    """Raise when TOOLS peel is on (``=1|2``) — no local fallthrough."""
    refuse_when(broker_tools_enabled, msg or TOOLS_EXCLUSIVE_MSG)


def map_broker_sandbox_http_miss(
    exc: BaseException,
    *,
    feature: str,
    miss_extra: dict[str, Any] | None = None,
    only_msg: str | None = None,
) -> dict[str, Any]:
    return map_domain_broker_http_miss(  # sak499-f
        exc,
        feature=feature,
        enabled=broker_sandbox_enabled,
        only=broker_sandbox_only,
        only_code="broker_sandbox_only",
        only_msg=only_msg or f"{feature} unavailable under NIMBUSWARE_BROKER_SANDBOX=2: {exc}",
        miss_extra=miss_extra,
    )


def map_broker_tools_http_miss(
    exc: BaseException,
    *,
    feature: str,
    miss_extra: dict[str, Any] | None = None,
    only_msg: str | None = None,
) -> dict[str, Any]:
    return map_domain_broker_http_miss(  # sak499-f
        exc,
        feature=feature,
        enabled=broker_tools_enabled,
        only=broker_tools_only,
        only_code="broker_tools_only",
        only_msg=only_msg or f"{feature} unavailable under NIMBUSWARE_BROKER_TOOLS=2: {exc}",
        miss_extra=miss_extra,
    )
