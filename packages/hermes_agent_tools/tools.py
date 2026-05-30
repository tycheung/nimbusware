from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from hermes_agent_tools.allowlist import (
    normalise_rel,
    path_in_plan,
    resolve_workspace_file,
    shell_from_string,
    validate_shell_invocation,
)


@dataclass(frozen=True)
class ToolResult:
    tool: str
    ok: bool
    output: str


def tool_read_file(workspace: Path, path: str, *, max_chars: int = 16000) -> ToolResult:
    try:
        fp = resolve_workspace_file(workspace, path)
        if not fp.is_file():
            return ToolResult("read", False, f"not a file: {path}")
        text = fp.read_text(encoding="utf-8")
        if len(text) > max_chars:
            text = text[:max_chars] + "\n…(truncated)"
        return ToolResult("read", True, text)
    except (OSError, ValueError) as exc:
        return ToolResult("read", False, str(exc))


def tool_grep(
    workspace: Path,
    pattern: str,
    *,
    paths: tuple[str, ...] | list[str] | None = None,
    max_matches: int = 40,
) -> ToolResult:
    if not pattern.strip():
        return ToolResult("grep", False, "pattern required")
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        return ToolResult("grep", False, f"invalid pattern: {exc}")

    scope = [normalise_rel(p) for p in (paths or []) if str(p).strip()]
    matches: list[str] = []
    ws = workspace.resolve()
    files: list[Path] = []
    if scope:
        for rel in scope:
            fp = ws / rel
            if fp.is_file():
                files.append(fp)
    else:
        files = [p for p in ws.rglob("*") if p.is_file() and ".git" not in p.parts]

    for fp in files:
        rel = str(fp.relative_to(ws)).replace("\\", "/")
        try:
            for i, line in enumerate(fp.read_text(encoding="utf-8").splitlines(), start=1):
                if rx.search(line):
                    matches.append(f"{rel}:{i}:{line[:200]}")
                    if len(matches) >= max_matches:
                        break
        except OSError:
            continue
        if len(matches) >= max_matches:
            break

    if not matches:
        return ToolResult("grep", True, "no matches")
    return ToolResult("grep", True, "\n".join(matches))


def tool_write_file(
    workspace: Path,
    path: str,
    content: str,
    *,
    allowed_paths: set[str],
) -> ToolResult:
    rel = normalise_rel(path)
    if not path_in_plan(rel, allowed_paths):
        return ToolResult("write", False, f"rejected path outside slice plan: {rel!r}")
    try:
        target = resolve_workspace_file(workspace, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult("write", True, f"wrote {rel}")
    except (OSError, ValueError) as exc:
        return ToolResult("write", False, str(exc))


def tool_run_shell(
    workspace: Path,
    command: str,
    args: list[str] | None = None,
    *,
    timeout_seconds: float = 120.0,
) -> ToolResult:
    try:
        if args is None and " " in command.strip():
            cmd, cmd_args = shell_from_string(command)
        else:
            cmd, cmd_args = validate_shell_invocation(command, list(args or []))
        proc = subprocess.run(
            [cmd, *cmd_args],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode == 0
        return ToolResult("shell", ok, out[:4000] or f"exit {proc.returncode}")
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return ToolResult("shell", False, str(exc))
