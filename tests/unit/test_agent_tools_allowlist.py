from __future__ import annotations

from pathlib import Path

import pytest

from agent_tools.tool_registry import (
    agent_tool_list_prompt,
    agent_tools_allowlist,
    is_agent_tool_enabled,
)
from agent_tools.tools import tool_find, tool_ls


def test_default_allowlist_excludes_find_ls() -> None:
    allow = agent_tools_allowlist()
    assert "read" in allow
    assert "find" not in allow
    assert "ls" not in allow


def test_allowlist_includes_find_when_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "NIMBUSWARE_AGENT_TOOLS",
        "read,write,edit,grep,shell,find,ls",
    )
    allow = agent_tools_allowlist()
    assert "find" in allow
    assert "ls" in allow
    assert "find" in agent_tool_list_prompt()


def test_tool_find_lists_matches(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "packages").mkdir()
    (ws / "packages" / "demo.py").write_text("x\n", encoding="utf-8")
    result = tool_find(ws, "demo", paths=["packages"])
    assert result.ok
    assert "demo.py" in result.output


def test_tool_ls_directory(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "a.py").write_text("x\n", encoding="utf-8")
    result = tool_ls(ws, ".")
    assert result.ok
    assert "a.py" in result.output


def test_is_agent_tool_enabled_respects_env(monkeypatch: pytest.MonkeyPatch) -> None:
    assert not is_agent_tool_enabled("find")
    monkeypatch.setenv("NIMBUSWARE_AGENT_TOOLS", "read,find")
    assert is_agent_tool_enabled("find")
    assert not is_agent_tool_enabled("write")
