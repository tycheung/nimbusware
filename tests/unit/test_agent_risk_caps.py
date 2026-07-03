from __future__ import annotations

from pathlib import Path

import pytest

from agent_tools.risk_caps import AgentRiskCaps, resolve_agent_risk_caps
from agent_tools.runtime import execute_slice_implement_agent
from orchestrator.micro_slice import parse_slice_plan
from orchestrator.slice_implement import slice_implement_mode


def test_resolve_agent_risk_caps_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_AGENT_MAX_TOOL_STEPS", raising=False)
    caps = resolve_agent_risk_caps()
    assert caps.max_tool_steps == 20
    assert caps.max_shell_invocations == 5


def test_agent_risk_cap_stops_excess_steps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_SLICE_IMPLEMENT", "agent")
    assert slice_implement_mode() == "agent"
    ws = tmp_path / "proj"
    ws.mkdir()
    for name in ("a.py", "b.py", "c.py"):
        (ws / name).write_text("# x\n", encoding="utf-8")
    plan = parse_slice_plan(
        {
            "slice_id": "slice-1",
            "target_paths": ["a.py", "b.py", "c.py"],
            "rationale": "touch file",
            "acceptance_criteria": "ok",
        },
    )
    caps = AgentRiskCaps(max_tool_steps=2, max_shell_invocations=5, max_write_bytes=99999)
    result = execute_slice_implement_agent(ws, plan, risk_caps=caps)
    assert "max_tool_steps=2" in result.log
