from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from agent_core.context_budget import truncate_for_active_read, truncate_shell_output
from nimbusware_agent_tools.allowlist import (
    normalise_rel,
    path_in_plan,
    resolve_workspace_file,
    shell_from_string,
    validate_shell_invocation,
)
from nimbusware_env.env_flags import nimbusware_read_max_chars


@dataclass(frozen=True)
class ToolResult:
    tool: str
    ok: bool
    output: str


def tool_read_file(workspace: Path, path: str, *, max_chars: int | None = None) -> ToolResult:
    cap = max_chars if max_chars is not None else nimbusware_read_max_chars()
    try:
        fp = resolve_workspace_file(workspace, path)
        if not fp.is_file():
            return ToolResult("read", False, f"not a file: {path}")
        text = truncate_for_active_read(fp.read_text(encoding="utf-8"), max_chars=cap)
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
    if not scope:
        return ToolResult("grep", False, "paths required (filesystem jail)")
    matches: list[str] = []
    ws = workspace.resolve()
    files: list[Path] = []
    for rel in scope:
        try:
            fp = resolve_workspace_file(ws, rel)
        except ValueError as exc:
            return ToolResult("grep", False, str(exc))
        if fp.is_file():
            files.append(fp)

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


def tool_edit_file(
    workspace: Path,
    path: str,
    old_text: str,
    new_text: str,
    *,
    allowed_paths: set[str],
    replace_all: bool = False,
) -> ToolResult:
    rel = normalise_rel(path)
    if not path_in_plan(rel, allowed_paths):
        return ToolResult("edit", False, f"rejected path outside slice plan: {rel!r}")
    if not old_text:
        return ToolResult("edit", False, "old_text required")
    try:
        target = resolve_workspace_file(workspace, rel)
        if not target.is_file():
            return ToolResult("edit", False, f"not a file: {rel}")
        content = target.read_text(encoding="utf-8")
        count = content.count(old_text)
        if count == 0:
            return ToolResult("edit", False, f"old_text not found in {rel}")
        if count > 1 and not replace_all:
            return ToolResult("edit", False, f"ambiguous: {count} matches in {rel}")
        updated = content.replace(old_text, new_text, count if replace_all else 1)
        target.write_text(updated, encoding="utf-8")
        added = new_text.count("\n") + (1 if new_text and not new_text.endswith("\n") else 0)
        removed = old_text.count("\n") + (1 if old_text and not old_text.endswith("\n") else 0)
        if new_text.endswith("\n") and added > 0:
            added = new_text.count("\n")
        if old_text.endswith("\n") and removed > 0:
            removed = old_text.count("\n")
        return ToolResult("edit", True, f"edited {rel} (+{added}/-{removed} lines)")
    except (OSError, ValueError) as exc:
        return ToolResult("edit", False, str(exc))


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


def tool_find(
    workspace: Path,
    pattern: str,
    *,
    paths: tuple[str, ...] | list[str] | None = None,
    max_matches: int = 40,
) -> ToolResult:
    if not pattern.strip():
        return ToolResult("find", False, "pattern required")
    ws = workspace.resolve()
    scope = [normalise_rel(p) for p in (paths or []) if str(p).strip()]
    roots: list[Path] = []
    if scope:
        for rel in scope:
            try:
                fp = resolve_workspace_file(ws, rel)
            except ValueError as exc:
                return ToolResult("find", False, str(exc))
            roots.append(fp)
    else:
        roots = [ws]
    rx = re.compile(re.escape(pattern), re.IGNORECASE)
    matches: list[str] = []
    for root in roots:
        walk_root = root if root.is_dir() else root.parent
        try:
            for fp in walk_root.rglob("*"):
                if not fp.is_file():
                    continue
                try:
                    fp.relative_to(ws)
                except ValueError:
                    continue
                rel = str(fp.relative_to(ws)).replace("\\", "/")
                if rx.search(rel) or rx.search(fp.name):
                    matches.append(rel)
                    if len(matches) >= max_matches:
                        break
        except OSError:
            continue
        if len(matches) >= max_matches:
            break
    if not matches:
        return ToolResult("find", True, "no matches")
    return ToolResult("find", True, "\n".join(matches))


def tool_ls(
    workspace: Path,
    path: str = ".",
    *,
    max_entries: int = 80,
) -> ToolResult:
    try:
        fp = resolve_workspace_file(workspace, path)
        if not fp.is_dir():
            return ToolResult("ls", False, f"not a directory: {path}")
        entries: list[str] = []
        for child in sorted(fp.iterdir(), key=lambda p: p.name.lower()):
            rel = str(child.relative_to(workspace.resolve())).replace("\\", "/")
            suffix = "/" if child.is_dir() else ""
            entries.append(f"{rel}{suffix}")
            if len(entries) >= max_entries:
                break
        return ToolResult("ls", True, "\n".join(entries) or "(empty)")
    except (OSError, ValueError) as exc:
        return ToolResult("ls", False, str(exc))


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
        from nimbusware_agent_tools.sandbox import run_subprocess_in_sandbox

        proc = run_subprocess_in_sandbox(
            workspace,
            [cmd, *cmd_args],
            timeout_seconds=timeout_seconds,
        )
        out = proc.combined_output
        ok = proc.returncode == 0
        tag = f"[{proc.backend}] " if proc.backend != "none" else ""
        bounded = truncate_shell_output(tag + out) or f"exit {proc.returncode}"
        return ToolResult("shell", ok, bounded)
    except (OSError, TimeoutError, ValueError) as exc:
        return ToolResult("shell", False, str(exc))
