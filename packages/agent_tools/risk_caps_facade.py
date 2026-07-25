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

    def to_metadata(self) -> dict[str, Any]:
        return {
            "max_steps": self.max_steps,
            "max_shells": self.max_shells,
            "max_writes": self.max_writes,
            "allow_network": self.allow_network,
            **self.extra,
            "mode": "broker",
            "removed": "sak412",
        }


PATCH_DEFAULT_CAPS = AgentRiskCaps()


def resolve_agent_risk_caps(*args: Any, **kwargs: Any) -> AgentRiskCaps:
    return AgentRiskCaps()
