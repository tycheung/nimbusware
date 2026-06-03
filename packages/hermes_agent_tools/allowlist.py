from __future__ import annotations

import os
import shlex
from pathlib import Path

ALLOWED_SHELL_COMMANDS = frozenset(
    {
        "pytest",
        "ruff",
        "python",
        "python3",
    },
)


def normalise_rel(path: str) -> str:
    return path.replace("\\", "/").lstrip("/")


def path_in_plan(rel: str, allowed: set[str]) -> bool:
    n = normalise_rel(rel)
    if not n or ".." in n.split("/"):
        return False
    return n in allowed


def resolve_workspace_file(workspace: Path, rel: str) -> Path:
    from hermes_agent_tools.filesystem_jail import assert_rel_allowed

    assert_rel_allowed(rel)
    ws = workspace.resolve()
    target = (ws / normalise_rel(rel)).resolve()
    if not str(target).startswith(str(ws)):
        msg = f"path escapes workspace: {rel!r}"
        raise ValueError(msg)
    return target


def validate_shell_invocation(command: str, args: list[str]) -> tuple[str, list[str]]:
    parts = [command.strip(), *[str(a) for a in args]]
    if not parts[0]:
        raise ValueError("shell command required")
    base = Path(parts[0]).name.lower()
    if base not in ALLOWED_SHELL_COMMANDS:
        raise ValueError(f"shell command not allowlisted: {parts[0]!r}")
    return parts[0], parts[1:]


def shell_from_string(command_line: str) -> tuple[str, list[str]]:
    parts = shlex.split(command_line, posix=os.name != "nt")
    if not parts:
        raise ValueError("empty shell command")
    return validate_shell_invocation(parts[0], parts[1:])
