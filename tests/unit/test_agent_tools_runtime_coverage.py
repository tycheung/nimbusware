from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from agent_tools.runtime import (
    AgentStep,
    _allowed_paths,
    _execute_step,
    _gather_context,
    _parse_steps,
    re_escape_simple,
)
from agent_tools.tools import ToolResult
from orchestrator.micro_slice import SlicePlan


def test_allowed_paths_normalizes() -> None:
    plan = SlicePlan(
        slice_id="s1",
        target_paths=["\\src\\a.py", "/src/b.py"],
        rationale="",
        acceptance_criteria=[],
    )
    assert _allowed_paths(plan) == {"src/a.py", "src/b.py"}


def test_parse_steps_from_edits_and_steps() -> None:
    assert _parse_steps({}) == []
    edit_steps = _parse_steps({"edits": [{"path": "a.py", "content": "x"}]})
    assert len(edit_steps) == 1
    assert edit_steps[0].tool == "write"
    read_steps = _parse_steps({"steps": [{"tool": "read", "path": "a.py"}]})
    assert read_steps[0].tool == "read"


def test_execute_step_unknown_tool() -> None:
    ws = MagicMock()
    out = _execute_step(ws, AgentStep("nope", {}), allowed=set(), timeout_seconds=1.0)
    assert out.ok is False


def test_gather_context_includes_rationale(tmp_path: Path) -> None:
    target = tmp_path / "pkg.py"
    target.write_text("hello", encoding="utf-8")
    plan = SlicePlan(
        slice_id="s1",
        target_paths=[str(target.name)],
        rationale="hello world",
        acceptance_criteria=[],
    )
    text = _gather_context(tmp_path, plan)
    assert "hello" in text
    assert re_escape_simple("a.b") == "a\\.b"


def test_execute_step_read_uses_tool(tmp_path: Path, monkeypatch) -> None:
    f = tmp_path / "a.txt"
    f.write_text("ok", encoding="utf-8")
    result = _execute_step(
        tmp_path,
        AgentStep("read", {"path": "a.txt"}),
        allowed={"a.txt"},
        timeout_seconds=1.0,
    )
    assert isinstance(result, ToolResult)
    assert result.ok
