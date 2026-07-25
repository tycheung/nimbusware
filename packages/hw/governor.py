"""Thin resource governor (`sak420-b`/`sak420-d`). Prefer broker capacity; legacy under dual-run/`=0`."""

from __future__ import annotations

from typing import Any

from broker_client.flags import broker_capacity_enabled
from hw.governor_legacy import ResourceGovernor
from hw.profile import HardwareProfile

_MSG = (
    "hw.governor local path unavailable under NIMBUSWARE_BROKER_CAPACITY=1|2; "
    "use SwissArmyNoife HTTP /v1/sak/capacity → governor_metadata_from_capacity"
)


def _legacy():
    from hw import governor_legacy as legacy

    return legacy


def _governor_from_flat(raw: dict[str, Any]) -> ResourceGovernor:
    return ResourceGovernor(
        max_system_ram_pct=float(raw.get("max_system_ram_pct", 75)),
        max_vram_pct=float(raw.get("max_vram_pct", 85)),
        reserve_ram_gb=float(raw.get("reserve_ram_gb", 2)),
        max_parallel_writer_stages=int(raw.get("max_parallel_writer_stages", 1)),
        allow_parallel_critics=bool(raw.get("allow_parallel_critics")),
        auto_adjust=bool(raw.get("auto_adjust", True)),
        hardware_tier=str(raw.get("hardware_tier") or "medium"),
    )


def _looks_like_governor_meta(raw: dict[str, Any]) -> bool:
    return "hardware_tier" in raw or "max_parallel_writer_stages" in raw


def governor_for_profile(profile: HardwareProfile) -> ResourceGovernor:
    """Broker-first governor; local legacy only when capacity flag is off."""
    if broker_capacity_enabled():
        from broker_client.capacity_bridge import try_broker_capacity_probe
        from broker_client.stage_bind.capacity import governor_metadata_from_capacity
        from hw.capacity_route import refuse_legacy

        hit = try_broker_capacity_probe()
        if hit is not None:
            meta = governor_metadata_from_capacity(hit)
            return _governor_from_flat(meta)
        refuse_legacy(_MSG)
    return _legacy().governor_for_profile(profile)


def governor_from_metadata(meta: dict[str, Any] | None) -> ResourceGovernor | None:
    """Parse run/API metadata into ``ResourceGovernor`` (`sak420-d`).

    Accepts:
    - ``{"resource_governor": {...}}`` (classic)
    - flat governor dicts
    - broker capacity probe dicts (``snapshot`` / passthrough) via mapper
    """
    if not isinstance(meta, dict):
        return None

    nested = meta.get("resource_governor")
    if isinstance(nested, dict):
        if _looks_like_governor_meta(nested):
            return _governor_from_flat(nested)
        if "snapshot" in nested or nested.get("capacity_source") == "broker":
            from broker_client.stage_bind.capacity import governor_metadata_from_capacity

            return _governor_from_flat(governor_metadata_from_capacity(nested))

    if _looks_like_governor_meta(meta):
        return _governor_from_flat(meta)

    if "snapshot" in meta or meta.get("capacity_source") == "broker":
        from broker_client.stage_bind.capacity import governor_metadata_from_capacity

        return _governor_from_flat(governor_metadata_from_capacity(meta))

    return None
