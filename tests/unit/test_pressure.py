from __future__ import annotations

from nimbusware_hw.governor import ResourceGovernor
from nimbusware_hw.pressure import pressure_limits_parallel, sample_pressure


def test_pressure_limits_parallel_block() -> None:
    assert pressure_limits_parallel("block", 4) == 1
    assert pressure_limits_parallel("throttle", 4) == 2


def test_sample_pressure_returns_level() -> None:
    gov = ResourceGovernor(max_system_ram_pct=75.0)
    level, details = sample_pressure(gov)
    assert level in ("ok", "warn", "throttle", "block")
    assert "tier" in details
