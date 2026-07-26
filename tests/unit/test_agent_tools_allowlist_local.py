"""Allowlist helpers still live locally after sak412 tool peel."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_tools.allowlist import path_in_plan, validate_shell_invocation


def test_path_in_plan() -> None:
    allowed = {"app.py", "lib/util.py"}
    assert path_in_plan("app.py", allowed)
    assert not path_in_plan("../secret.py", allowed)


def test_shell_allowlist() -> None:
    validate_shell_invocation("pytest", ["-q"])
    with pytest.raises(ValueError, match="not allowlisted"):
        validate_shell_invocation("rm", ["-rf", "/"])


def test_workspace_paths_exist(tmp_path: Path) -> None:
    assert tmp_path.is_dir()
