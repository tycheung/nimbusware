"""Thin hardware profile cache (`sak419-c` / `sak433-c`). Prefer broker; refuse under CAPACITY=1|2 miss."""

from __future__ import annotations

from broker_client.flags import broker_capacity_enabled
from hw.capacity_route import refuse_legacy
from hw.profile import HardwareProfile, profile_from_probe

_MSG = (
    "hw.cache local path unavailable under NIMBUSWARE_BROKER_CAPACITY=1|2; "
    "use SwissArmyNoife HTTP /v1/sak/capacity"
)

_broker_cached: HardwareProfile | None = None


def _legacy():
    from hw import cache_legacy as legacy

    return legacy


def get_cached_profile(*, fresh: bool = False) -> HardwareProfile:
    """Broker-first cached profile; local legacy only when capacity flag is off."""
    global _broker_cached
    if broker_capacity_enabled():
        from broker_client.capacity_bridge import try_broker_probe_dict

        if fresh:
            _broker_cached = None
        if _broker_cached is not None and not fresh:
            return _broker_cached
        hit = try_broker_probe_dict()
        if hit is not None:
            _broker_cached = profile_from_probe(hit)
            return _broker_cached
        refuse_legacy(_MSG)
    return _legacy().get_cached_profile(fresh=fresh)


def rescan_hardware() -> HardwareProfile:
    return get_cached_profile(fresh=True)
