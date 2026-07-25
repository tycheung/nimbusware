"""Dual-run capacity bridge at orchestrator edge (`sak417-f`, `sak418-d`).

Thin orchestrator hook — delegates to ``broker_client.capacity_bridge``.
"""

from __future__ import annotations

from typing import Any

from broker_client.capacity_bridge import (
    try_broker_capacity_pressure as _broker_capacity_pressure,
)
from broker_client.capacity_bridge import (
    try_broker_capacity_probe as _broker_capacity_probe,
)
from broker_client.capacity_bridge import (
    try_broker_parallel_writer_stages as _broker_parallel_writer_stages,
)


def try_broker_capacity_probe() -> dict | None:
    """If ``NIMBUSWARE_BROKER_CAPACITY`` is 1|2, call broker capacity bridge; else ``None``."""
    return _broker_capacity_probe()


def try_broker_capacity_pressure(
    *,
    max_system_ram_pct: float = 75.0,
) -> dict[str, Any] | None:
    """Derived pressure from broker capacity probe when the capacity flag is on."""
    return _broker_capacity_pressure(max_system_ram_pct=max_system_ram_pct)


def try_broker_parallel_writer_stages() -> int | None:
    """Parallel writer cap from broker capacity when the capacity flag is on."""
    return _broker_parallel_writer_stages()
