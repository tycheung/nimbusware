"""Optional broker compute work at the broker_client edge (`sak407-d` / `sak435-a`).

Under ``NIMBUSWARE_BROKER_COMPUTE=1|2``, broker failure re-raises (no ``None`` soft miss).
"""

from __future__ import annotations

from typing import Any

from broker_client.flags import broker_compute_enabled
from broker_client.stage_bind import compute_work_via_broker


def try_broker_compute_work(payload: dict[str, Any]) -> dict | None:
    """Return broker compute result when enabled.

    Disabled (``=0``): ``None``.
    Peel (``=1|2``): return result or re-raise on failure (`sak435-a`).
    """
    if not broker_compute_enabled():
        return None
    return compute_work_via_broker(payload)
