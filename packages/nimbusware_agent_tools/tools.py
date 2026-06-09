from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from agent_core.context_budget import (
    strip_ansi,
    truncate_for_active_read,
    truncate_shell_output,
)
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
    llm_output: str
    audit_output: str

    @property
    def output(self) -> str:
        return self.llm_output


def _result(tool: str, ok: bool, llm: str, *, audit: str | None = None) -> ToolResult:
    return ToolResult(
        tool=tool,
        ok=ok,
        llm_output=llm,
        audit_output=audit if audit is not None else llm,
    )


def tool_read_file(workspace: Path, path: str, *, max_chars: int | None = None) -> ToolResult:
    cap = max_chars if max_chars is not None else nimbusware_read_max_chars()
    try:
        fp = resolve_workspace_file(workspace, path)
        if not fp.is_file():
            return _result("read", False, f"not a file: {path}")
        raw = fp.read_text(encoding="utf-8")
        rel = str(fp.relative_to(workspace.resolve())).replace("\\", "/")
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        line_count = raw.count("\n") + (1 if raw and not raw.endswith("\n") else 0)
        llm = truncate_for_active_read(raw, max_chars=cap)
        audit = f"{rel} sha256={digest} lines={line_count}"
        return _result("read", True, llm, audit=audit)
    except (OSError, ValueError) as exc:
        return _result("read", False, str(exc))


def tool_grep(
    workspace: Path,
    pattern: str,
    *,
    paths: tuple[str, ...] | list[str] | None = None,
    max_matches: int = 40,
) -> ToolResult:
    if not pattern.strip():
        return _result("grep", False, "pattern required")
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        return _result("grep", False, f"invalid pattern: {exc}")

    scope = [normalise_rel(p) for p in (paths or []) if str(p).strip()]
    if not scope:
        return _result("grep", False, "paths required (filesystem jail)")
    matches: list[str] = []
    ws = workspace.resolve()
    files: list[Path] = []
    for rel in scope:
        try:
            fp = resolve_workspace_file(ws, rel)
        except ValueError as exc:
            return _result("grep", False, str(exc))
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
        return _result("grep", True, "no matches")
    return _result("grep", True, "\n".join(matches))


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
        return _result("edit", False, f"rejected path outside slice plan: {rel!r}")
    if not old_text:
        return _result("edit", False, "old_text required")
    try:
        target = resolve_workspace_file(workspace, rel)
        if not target.is_file():
            return _result("edit", False, f"not a file: {rel}")
        content = target.read_text(encoding="utf-8")
        count = content.count(old_text)
        if count == 0:
            return _result("edit", False, f"old_text not found in {rel}")
        if count > 1 and not replace_all:
            return _result("edit", False, f"ambiguous: {count} matches in {rel}")
        updated = content.replace(old_text, new_text, count if replace_all else 1)
        target.write_text(updated, encoding="utf-8")
        delta = len(new_text.encode("utf-8")) - len(old_text.encode("utf-8"))
        llm = f"edited {rel} (+{delta} bytes)"
        audit = f"{rel} delta={delta} bytes"
        return _result("edit", True, llm, audit=audit)
    except (OSError, ValueError) as exc:
        return _result("edit", False, str(exc))


def tool_write_file(
    workspace: Path,
    path: str,
    content: str,
    *,
    allowed_paths: set[str],
) -> ToolResult:
    rel = normalise_rel(path)
    if not path_in_plan(rel, allowed_paths):
        return _result("write", False, f"rejected path outside slice plan: {rel!r}")
    try:
        target = resolve_workspace_file(workspace, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        nbytes = len(content.encode("utf-8"))
        llm = f"wrote {rel}"
        audit = f"{rel} +{nbytes} bytes"
        return _result("write", True, llm, audit=audit)
    except (OSError, ValueError) as exc:
        return _result("write", False, str(exc))


def tool_find(
    workspace: Path,
    pattern: str,
    *,
    paths: tuple[str, ...] | list[str] | None = None,
    max_matches: int = 40,
) -> ToolResult:
    if not pattern.strip():
        return _result("find", False, "pattern required")
    ws = workspace.resolve()
    scope = [normalise_rel(p) for p in (paths or []) if str(p).strip()]
    roots: list[Path] = []
    if scope:
        for rel in scope:
            try:
                fp = resolve_workspace_file(ws, rel)
            except ValueError as exc:
                return _result("find", False, str(exc))
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
        return _result("find", True, "no matches")
    return _result("find", True, "\n".join(matches))


def tool_ls(
    workspace: Path,
    path: str = ".",
    *,
    max_entries: int = 80,
) -> ToolResult:
    try:
        fp = resolve_workspace_file(workspace, path)
        if not fp.is_dir():
            return _result("ls", False, f"not a directory: {path}")
        entries: list[str] = []
        for child in sorted(fp.iterdir(), key=lambda p: p.name.lower()):
            rel = str(child.relative_to(workspace.resolve())).replace("\\", "/")
            suffix = "/" if child.is_dir() else ""
            entries.append(f"{rel}{suffix}")
            if len(entries) >= max_entries:
                break
        return _result("ls", True, "\n".join(entries) or "(empty)")
    except (OSError, ValueError) as exc:
        return _result("ls", False, str(exc))


def tool_browser_act(
    *,
    base_url: str,
    action: str,
    selector: str = "body",
    value: str = "",
    url: str = "",
) -> ToolResult:
    from nimbusware_orchestrator.browser_controller import run_ui_flow
    from nimbusware_orchestrator.ui_flow_dsl import UiFlowDefinition, UiFlowStep

    kind = action.strip().lower()
    allowed = {
        "goto",
        "click",
        "fill",
        "press",
        "select",
        "wait_for",
        "expect_text",
        "expect_visible",
    }
    if kind not in allowed:
        return _result("browser_act", False, f"unsupported action: {action}")
    step = UiFlowStep(
        kind=kind,  # type: ignore[arg-type]
        selector=selector or None,
        value=value or None,
        url=url or (value if kind == "goto" else None),
    )
    outcome = run_ui_flow(base_url, UiFlowDefinition(flow_id="browser_act", steps=[step]))
    detail = outcome.detail or ("pass" if outcome.passed else "fail")
    return _result("browser_act", outcome.passed, detail)


def tool_write_ui_flow(workspace: Path, flow_id: str, yaml_body: str) -> ToolResult:
    import yaml

    from nimbusware_orchestrator.ui_flow_dsl import load_ui_flow
    from nimbusware_orchestrator.ui_flow_synthesis import validate_ui_flow_yaml, write_draft_ui_flow

    try:
        raw = yaml.safe_load(yaml_body) or {}
    except yaml.YAMLError as exc:
        return _result("write_ui_flow", False, str(exc))
    if not isinstance(raw, dict):
        return _result("write_ui_flow", False, "yaml must be a mapping")
    errors = validate_ui_flow_yaml(raw)
    if errors:
        return _result("write_ui_flow", False, "; ".join(errors))
    flow = load_ui_flow(flow_id, raw)
    path = write_draft_ui_flow(workspace, flow)
    return _result("write_ui_flow", True, str(path))


def tool_run_ui_regression(workspace: Path, *, base_url: str, flow_id: str) -> ToolResult:
    from nimbusware_orchestrator.browser_controller import run_ui_flow
    from nimbusware_orchestrator.launch_flow_resolver import resolve_ui_flow

    flow, _ = resolve_ui_flow(workspace, flow_id=flow_id)
    if flow is None:
        return _result("run_ui_regression", False, f"unknown flow: {flow_id}")
    outcome = run_ui_flow(base_url, flow)
    return _result("run_ui_regression", outcome.passed, outcome.detail)


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
        raw = tag + out
        audit = truncate_shell_output(raw) or f"exit {proc.returncode}"
        llm = truncate_shell_output(strip_ansi(raw)) or f"exit {proc.returncode}"
        return _result("shell", ok, llm, audit=audit)
    except (OSError, TimeoutError, ValueError) as exc:
        return _result("shell", False, str(exc))
