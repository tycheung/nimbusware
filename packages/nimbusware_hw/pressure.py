from __future__ import annotations

from typing import Any, Literal

from nimbusware_env.env_flags import env_bool
from nimbusware_hw.cache import get_cached_profile
from nimbusware_hw.governor import ResourceGovernor, governor_for_profile
from nimbusware_hw.probe import available_memory_gb

PressureLevel = Literal["ok", "warn", "throttle", "block"]


def sample_pressure(
    governor: ResourceGovernor | None = None,
) -> tuple[PressureLevel, dict[str, Any]]:
    profile = get_cached_profile()
    gov = governor or governor_for_profile(profile)
    total_gb, avail_gb = available_memory_gb()
    details: dict[str, Any] = {
        "tier": profile.tier,
        "max_system_ram_pct": gov.max_system_ram_pct,
    }
    if total_gb is None or avail_gb is None:
        return "ok", {**details, "reason": "ram_probe_unavailable"}
    used_pct = ((total_gb - avail_gb) / total_gb * 100.0) if total_gb > 0 else 0.0
    details["ram_used_pct"] = round(used_pct, 1)
    cap = gov.max_system_ram_pct
    if used_pct >= cap + 10:
        return "block", {**details, "reason": "ram_over_cap"}
    if used_pct >= cap + 5:
        return "throttle", {**details, "reason": "ram_near_cap"}
    if used_pct >= cap:
        return "warn", {**details, "reason": "ram_at_cap"}
    return "ok", details


def pressure_limits_parallel(level: PressureLevel, base_cap: int) -> int:
    if level == "block":
        return 1
    if level == "throttle":
        return max(1, base_cap // 2)
    return base_cap


def should_defer_memory_rebuild(level: PressureLevel) -> bool:
    return level != "ok"


def should_degrade_llm_to_stub(level: PressureLevel) -> bool:
    if level != "block":
        return False
    return env_bool("HERMES_PRESSURE_DEGRADE_STUB", default=True)
