from __future__ import annotations

from env.env_flags import hw_fixture
from hw.probe import probe_hardware
from hw.profile import HardwareProfile, profile_from_probe

_cached: HardwareProfile | None = None


def get_cached_profile(*, fresh: bool = False) -> HardwareProfile:
    global _cached
    fixture = hw_fixture()
    if fresh or _cached is None:
        raw = probe_hardware(fixture=fixture)
        _cached = profile_from_probe(raw)
    return _cached


def rescan_hardware() -> HardwareProfile:
    return get_cached_profile(fresh=True)
