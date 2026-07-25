"""Runtime entry after sak412 runtime.py thin delete."""
from __future__ import annotations

from typing import Any


def execute_slice_implement_agent(*args: Any, **kwargs: Any) -> Any:
    raise RuntimeError(
        "agent_tools.runtime removed (sak412); use sandbox_bridge / broker tools"
    )
