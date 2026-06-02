from __future__ import annotations

import os

from nimbusware_hw.probe import probe_hardware
from nimbusware_hw.profile import HardwareProfile, profile_from_probe

_cached: HardwareProfile | None = None


def get_cached_profile(*, fresh: bool = False) -> HardwareProfile:
    global _cached
    fixture = os.environ.get("NIMBUSWARE_HW_FIXTURE", "").strip() or None
    if fresh or _cached is None:
        raw = probe_hardware(fixture=fixture)
        _cached = profile_from_probe(raw)
    return _cached


def rescan_hardware() -> HardwareProfile:
    return get_cached_profile(fresh=True)
