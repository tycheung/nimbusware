"""Thin hardware pressure (`sak418-g`). Prefer broker capacity; legacy under dual-run/`=0`."""

from __future__ import annotations

from typing import Any, Literal

from broker_client.flags import broker_capacity_enabled
from env.env_flags import env_bool
from hw.governor import ResourceGovernor

PressureLevel = Literal["ok", "warn", "throttle", "block"]

_MSG = (
    "hw.pressure local path unavailable under NIMBUSWARE_BROKER_CAPACITY=1|2; "
    "use SwissArmyNoife capacity probe / capacity.pressure"
)


def _legacy():
    from hw import pressure_legacy as legacy

    return legacy


def sample_pressure(
    governor: ResourceGovernor | None = None,
) -> tuple[PressureLevel, dict[str, Any]]:
    """Broker-first pressure; local legacy only when capacity flag is off."""
    if broker_capacity_enabled():
        from broker_client.capacity_bridge import try_broker_capacity_pressure
        from hw.capacity_route import refuse_legacy

        max_pct = 75.0
        if governor is not None:
            max_pct = float(governor.max_system_ram_pct)
        hit = try_broker_capacity_pressure(max_system_ram_pct=max_pct)
        if hit is not None:
            level = hit.get("level", "ok")
            details = dict(hit.get("details") or {})
            if governor is not None:
                details.setdefault("tier", governor.hardware_tier)
                details.setdefault("max_system_ram_pct", governor.max_system_ram_pct)
            if level in ("ok", "warn", "throttle", "block"):
                return level, details  # type: ignore[return-value]
        refuse_legacy(_MSG)
    return _legacy().sample_pressure(governor)


def pressure_limits_parallel(level: PressureLevel, base_cap: int) -> int:
    # sak489-c: under CAPACITY peel use inline cap math (no legacy hw import soft path).
    if broker_capacity_enabled():
        if level == "block":
            return 1
        if level == "throttle":
            return max(1, base_cap // 2)
        return base_cap
    return _legacy().pressure_limits_parallel(level, base_cap)


def should_defer_memory_rebuild(level: PressureLevel) -> bool:
    return level != "ok"


def should_degrade_llm_to_stub(level: PressureLevel) -> bool:
    if level != "block":
        return False
    return env_bool("NIMBUSWARE_PRESSURE_DEGRADE_STUB", default=True)
