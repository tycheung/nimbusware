"""Per-run autonomous agent tool limits (OpenHands-style guardrails)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentRiskCaps:
    max_tool_steps: int = 20
    max_shell_invocations: int = 5
    max_write_bytes: int = 262_144

    def to_metadata(self) -> dict[str, int]:
        return {
            "max_tool_steps": self.max_tool_steps,
            "max_shell_invocations": self.max_shell_invocations,
            "max_write_bytes": self.max_write_bytes,
        }


class RiskCapExceeded(Exception):
    def __init__(self, cap: str, limit: int) -> None:
        super().__init__(f"agent risk cap exceeded: {cap} (limit {limit})")
        self.cap = cap
        self.limit = limit


def _bounded_int(key: str, default: int, *, lo: int, hi: int) -> int:
    from nimbusware_env.settings_resolve import resolve_int

    return max(lo, min(hi, resolve_int(key, default=default)))


def resolve_agent_risk_caps() -> AgentRiskCaps:
    return AgentRiskCaps(
        max_tool_steps=_bounded_int("HERMES_AGENT_MAX_TOOL_STEPS", 20, lo=1, hi=200),
        max_shell_invocations=_bounded_int(
            "HERMES_AGENT_MAX_SHELL_INVOCATIONS",
            5,
            lo=0,
            hi=50,
        ),
        max_write_bytes=_bounded_int(
            "HERMES_AGENT_MAX_WRITE_BYTES",
            262_144,
            lo=1024,
            hi=2_097_152,
        ),
    )


def caps_from_metadata(raw: Any) -> AgentRiskCaps | None:
    if not isinstance(raw, dict):
        return None
    try:
        return AgentRiskCaps(
            max_tool_steps=int(raw.get("max_tool_steps", 20)),
            max_shell_invocations=int(raw.get("max_shell_invocations", 5)),
            max_write_bytes=int(raw.get("max_write_bytes", 262_144)),
        )
    except (TypeError, ValueError):
        return None
