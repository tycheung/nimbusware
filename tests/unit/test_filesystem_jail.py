from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_agent_tools.allowlist import resolve_workspace_file
from nimbusware_agent_tools.filesystem_jail import FilesystemJailPolicy
from nimbusware_agent_tools.tools import tool_grep, tool_read_file


def test_denies_env_and_git_paths() -> None:
    pol = FilesystemJailPolicy(enabled=True)
    assert pol.rel_denied(".env") is not None
    assert pol.rel_denied("config/.env.local") is not None
    assert pol.rel_denied(".git/config") is not None
    assert pol.rel_denied("app/main.py") is None


def test_resolve_workspace_blocks_env(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".env").write_text("SECRET=1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="filesystem jail"):
        resolve_workspace_file(ws, ".env")


def test_tool_read_allows_normal_file(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "app.py").write_text("ok\n", encoding="utf-8")
    result = tool_read_file(ws, "app.py")
    assert result.ok


def test_grep_requires_paths(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "app.py").write_text("inventory\n", encoding="utf-8")
    result = tool_grep(ws, "inventory")
    assert not result.ok
    scoped = tool_grep(ws, "inventory", paths=["app.py"])
    assert scoped.ok
