"""Runtime entry after sak412 runtime.py thin delete."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentStep:
    """Legacy step shape kept for projections/tests; runtime loop was peeled."""

    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)


def execute_slice_implement_agent(*args: Any, **kwargs: Any) -> Any:
    raise RuntimeError("agent_tools.runtime removed (sak412); use sandbox_bridge / broker tools")
