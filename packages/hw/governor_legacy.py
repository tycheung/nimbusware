from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from env.env_flags import env_str, env_truthy, nimbusware_max_parallel_writers
from env.settings_resolve import resolve_bool
from hw.profile import HardwareProfile


@dataclass(frozen=True)
class ResourceGovernor:
    max_system_ram_pct: float = 75.0
    max_vram_pct: float = 85.0
    reserve_ram_gb: float = 2.0
    max_parallel_writer_stages: int = 1
    allow_parallel_critics: bool = False
    auto_adjust: bool = True
    hardware_tier: str = "medium"

    def to_metadata(self) -> dict[str, Any]:
        return {
            "max_system_ram_pct": self.max_system_ram_pct,
            "max_vram_pct": self.max_vram_pct,
            "reserve_ram_gb": self.reserve_ram_gb,
            "max_parallel_writer_stages": self.max_parallel_writer_stages,
            "allow_parallel_critics": self.allow_parallel_critics,
            "auto_adjust": self.auto_adjust,
            "hardware_tier": self.hardware_tier,
        }


def _env_float(name: str, default: float) -> float:
    raw = env_str(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def governor_for_profile(profile: HardwareProfile) -> ResourceGovernor:
    tier = profile.tier
    if tier == "strong":
        parallel = 3
        ram_pct = 80.0
    elif tier == "medium":
        parallel = 2
        ram_pct = 75.0
    else:
        parallel = 1
        ram_pct = 70.0
    override = nimbusware_max_parallel_writers()
    parallel_stages = override if override is not None else parallel
    return ResourceGovernor(
        max_system_ram_pct=_env_float("NIMBUSWARE_MAX_SYSTEM_RAM_PCT", ram_pct),
        max_vram_pct=_env_float("NIMBUSWARE_MAX_VRAM_PCT", 85.0),
        reserve_ram_gb=_env_float("NIMBUSWARE_RESERVE_RAM_GB", 2.0),
        max_parallel_writer_stages=parallel_stages,
        allow_parallel_critics=env_truthy("NIMBUSWARE_ALLOW_PARALLEL_CRITICS"),
        auto_adjust=resolve_bool("NIMBUSWARE_HW_AUTO_ADJUST", default=True),
        hardware_tier=tier,
    )


def governor_from_metadata(meta: dict[str, Any] | None) -> ResourceGovernor | None:
    if not isinstance(meta, dict):
        return None
    raw = meta.get("resource_governor")
    if not isinstance(raw, dict):
        return None
    return ResourceGovernor(
        max_system_ram_pct=float(raw.get("max_system_ram_pct", 75)),
        max_vram_pct=float(raw.get("max_vram_pct", 85)),
        reserve_ram_gb=float(raw.get("reserve_ram_gb", 2)),
        max_parallel_writer_stages=int(raw.get("max_parallel_writer_stages", 1)),
        allow_parallel_critics=bool(raw.get("allow_parallel_critics")),
        auto_adjust=bool(raw.get("auto_adjust", True)),
        hardware_tier=str(raw.get("hardware_tier") or "medium"),
    )
