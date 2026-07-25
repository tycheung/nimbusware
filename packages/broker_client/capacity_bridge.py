"""Optional broker capacity probe at the broker_client edge (`sak417-e` / `sak435-a`).

Under ``NIMBUSWARE_BROKER_CAPACITY=1|2``, broker failure re-raises (no ``None`` soft miss).
"""

from __future__ import annotations

from typing import Any

from broker_client.flags import broker_capacity_enabled
from broker_client.stage_bind.capacity import (
    capacity_pressure_via_broker,
    capacity_probe_via_broker,
    parallel_writer_stages_from_capacity,
    probe_dict_from_capacity,
)


def try_broker_capacity_probe() -> dict | None:
    """Return broker capacity probe when enabled.

    Disabled (``=0``): ``None``.
    Peel (``=1|2``): return result or re-raise on failure (`sak435-a`).
    """
    if not broker_capacity_enabled():
        return None
    return capacity_probe_via_broker()


def try_broker_capacity_pressure(
    *,
    max_system_ram_pct: float = 75.0,
) -> dict[str, Any] | None:
    if not broker_capacity_enabled():
        return None
    return capacity_pressure_via_broker(max_system_ram_pct=max_system_ram_pct)


def try_broker_parallel_writer_stages() -> int | None:
    probe = try_broker_capacity_probe()
    if probe is None:
        return None
    return parallel_writer_stages_from_capacity(probe)


def try_broker_probe_dict() -> dict[str, Any] | None:
    probe = try_broker_capacity_probe()
    if probe is None:
        return None
    return probe_dict_from_capacity(probe)
