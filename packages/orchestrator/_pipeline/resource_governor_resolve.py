from __future__ import annotations

from typing import Any

from broker_client.flags import broker_capacity_enabled
from hw.cache import get_cached_profile
from hw.capacity_route import refuse_legacy
from hw.governor import governor_for_profile
from hw.profile import profile_from_probe
from orchestrator.capacity_broker_bridge import try_broker_capacity_probe

_MSG = (
    "resource_governor_resolve unavailable under "
    "NIMBUSWARE_BROKER_CAPACITY=1|2; use SwissArmyNoife /v1/sak/capacity"
)


def resolve_resource_governor() -> tuple[Any, dict[str, Any]]:
    """Return ``(hw_profile, resource_governor)``.

    Prefer broker capacity probe when the capacity flag is enabled and the call
    succeeds. Under ``CAPACITY=1|2``, broker miss refuses local fallthrough
    (`sak433-d`). Local ``get_cached_profile`` only when capacity flag is off.
    """
    broker_capacity = try_broker_capacity_probe()
    if broker_capacity is not None:
        from broker_client.stage_bind.capacity import (
            governor_metadata_from_capacity,
            probe_dict_from_capacity,
        )

        hw_profile = profile_from_probe(probe_dict_from_capacity(broker_capacity))
        resource_governor = governor_metadata_from_capacity(broker_capacity)
        return hw_profile, resource_governor

    if broker_capacity_enabled():
        refuse_legacy(_MSG)

    hw_profile = get_cached_profile()
    meta = governor_for_profile(hw_profile).to_metadata()
    meta.setdefault("capacity_source", "local")
    return hw_profile, meta
