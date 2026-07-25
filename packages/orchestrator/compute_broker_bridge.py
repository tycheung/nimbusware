"""Dual-run compute bridge at orchestrator edge (`sak407-h`).

Thin orchestrator hook for stage wire — delegates to ``broker_client.compute_bridge``.
Wired from ``worker_cli`` and ``pipeline_hook``; see ``docs/peel-compute-stage-wire.md``.
"""

from __future__ import annotations

from typing import Any

from broker_client.compute_bridge import try_broker_compute_work as _broker_compute_work


def try_broker_compute_work(payload: dict[str, Any]) -> dict | None:
    """If ``NIMBUSWARE_BROKER_COMPUTE=1``, call broker compute bridge; else ``None``."""
    return _broker_compute_work(payload)
