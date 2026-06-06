from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from agent_core.context_budget import strip_ansi
from nimbusware_agent_tools.tools import ToolResult, _result, tool_read_file, tool_run_shell


def test_output_property_aliases_llm_output() -> None:
    tr = _result("grep", True, "llm text", audit="audit text")
    assert tr.output == tr.llm_output == "llm text"
    assert tr.audit_output == "audit text"


def test_read_audit_metadata(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "demo.py").write_text("line1\nline2\n", encoding="utf-8")
    result = tool_read_file(ws, "demo.py")
    assert result.ok
    assert "line1" in result.llm_output
    assert "demo.py" in result.audit_output
    assert "sha256=" in result.audit_output
    assert "lines=2" in result.audit_output
    assert result.output == result.llm_output


def test_shell_strips_ansi_for_llm() -> None:
    colored = "\x1b[31merror\x1b[0m plain"
    assert strip_ansi(colored) == "error plain"
    ws = Path("/tmp/ws")
    proc = MagicMock()
    proc.combined_output = colored
    proc.returncode = 1
    proc.backend = "none"
    with (
        patch("nimbusware_agent_tools.sandbox.run_subprocess_in_sandbox", return_value=proc),
        patch(
            "nimbusware_agent_tools.tools.validate_shell_invocation",
            return_value=("pytest", ["-q"]),
        ),
    ):
        result = tool_run_shell(ws, "pytest", ["-q"])
    assert result.ok is False
    assert "\x1b[" not in result.llm_output
    assert "error" in result.llm_output
    assert "\x1b[31m" in result.audit_output


def test_tool_result_backward_compat_fields() -> None:
    tr = ToolResult(tool="read", ok=True, llm_output="content", audit_output="meta")
    assert tr.output == "content"
