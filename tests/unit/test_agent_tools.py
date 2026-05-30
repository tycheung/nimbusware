from __future__ import annotations

from pathlib import Path

import pytest

from hermes_agent_tools.allowlist import path_in_plan, validate_shell_invocation
from hermes_agent_tools.runtime import execute_slice_implement_agent
from hermes_agent_tools.tools import tool_grep, tool_read_file, tool_write_file
from hermes_orchestrator.micro_slice import parse_slice_plan
from hermes_orchestrator.slice_implement import slice_implement_mode


def test_path_in_plan() -> None:
    allowed = {"app.py", "lib/util.py"}
    assert path_in_plan("app.py", allowed)
    assert not path_in_plan("../secret.py", allowed)


def test_shell_allowlist() -> None:
    validate_shell_invocation("pytest", ["-q"])
    with pytest.raises(ValueError, match="not allowlisted"):
        validate_shell_invocation("rm", ["-rf", "/"])


def test_tool_read_write_roundtrip(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    target = ws / "app.py"
    target.write_text("hello\n", encoding="utf-8")
    read = tool_read_file(ws, "app.py")
    assert read.ok
    allowed = {"app.py"}
    write = tool_write_file(ws, "app.py", "hello world\n", allowed_paths=allowed)
    assert write.ok
    assert "world" in target.read_text(encoding="utf-8")


def test_tool_grep_finds_line(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "app.py").write_text("def inventory():\n    pass\n", encoding="utf-8")
    result = tool_grep(ws, "inventory", paths=["app.py"])
    assert result.ok
    assert "inventory" in result.output


def test_execute_slice_implement_agent_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_SLICE_IMPLEMENT", "agent")
    assert slice_implement_mode() == "agent"
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "packages/hermes_orchestrator").mkdir(parents=True)
    (ws / "packages/hermes_orchestrator/micro_slice.py").write_text("# x\n", encoding="utf-8")
    plan = parse_slice_plan(
        {
            "slice_id": "slice-1",
            "target_paths": ["packages/hermes_orchestrator/micro_slice.py"],
            "rationale": "inventory",
        },
    )
    result = execute_slice_implement_agent(ws, plan)
    assert result.mode == "agent"
