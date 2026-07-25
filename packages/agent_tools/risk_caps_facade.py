"""Risk caps stub after sak412 risk_caps.py delete."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentRiskCaps:
    max_steps: int = 0
    max_shells: int = 0
    max_writes: int = 0
    allow_network: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


PATCH_DEFAULT_CAPS = AgentRiskCaps()


def resolve_agent_risk_caps(*args: Any, **kwargs: Any) -> AgentRiskCaps:
    return AgentRiskCaps()
