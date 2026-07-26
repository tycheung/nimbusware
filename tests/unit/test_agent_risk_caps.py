from __future__ import annotations

from agent_tools.risk_caps_facade import AgentRiskCaps, resolve_agent_risk_caps
import pytest


def test_resolve_agent_risk_caps_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_AGENT_MAX_TOOL_STEPS", raising=False)
    caps = resolve_agent_risk_caps()
    assert caps.max_tool_steps == 20
    assert caps.max_shell_invocations == 5


def test_agent_risk_caps_metadata_roundtrip() -> None:
    caps = AgentRiskCaps(max_tool_steps=2, max_shell_invocations=5, max_write_bytes=99999)
    meta = caps.to_metadata()
    assert meta["max_tool_steps"] == 2
    assert meta["max_shell_invocations"] == 5
