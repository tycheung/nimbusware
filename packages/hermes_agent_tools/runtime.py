from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hermes_agent_tools.tools import (
    ToolResult,
    tool_grep,
    tool_read_file,
    tool_run_shell,
    tool_write_file,
)
from hermes_orchestrator.micro_slice import SlicePlan
from hermes_orchestrator.slice_implement import SliceImplementResult
from hermes_orchestrator.slice_patch_apply import apply_slice_file_edits


@dataclass(frozen=True)
class AgentStep:
    tool: str
    arguments: dict[str, Any]


def _allowed_paths(plan: SlicePlan) -> set[str]:
    return {p.replace("\\", "/").lstrip("/") for p in plan.target_paths}


def _gather_context(workspace: Any, plan: SlicePlan) -> str:
    sections: list[str] = []
    for rel in plan.target_paths[:5]:
        result = tool_read_file(workspace, rel)
        sections.append(f"=== read {rel} ===\n{result.output}")
    if plan.rationale.strip():
        grep_result = tool_grep(
            workspace,
            re_escape_simple(plan.rationale.split()[0]) if plan.rationale.split() else "def",
            paths=plan.target_paths,
        )
        sections.append(f"=== grep ===\n{grep_result.output}")
    return "\n".join(sections)[:14000]


def re_escape_simple(token: str) -> str:
    return re.escape(token)


def _parse_steps(data: dict[str, Any]) -> list[AgentStep]:
    steps_raw = data.get("steps")
    if not isinstance(steps_raw, list):
        edits = data.get("edits")
        if isinstance(edits, list):
            return [
                AgentStep("write", {"path": e.get("path"), "content": e.get("content")})
                for e in edits
                if isinstance(e, dict) and e.get("path")
            ]
        return []
    steps: list[AgentStep] = []
    for item in steps_raw:
        if not isinstance(item, dict):
            continue
        tool = str(item.get("tool") or "").strip().lower()
        if tool:
            steps.append(AgentStep(tool=tool, arguments=dict(item)))
    return steps


def _execute_step(
    workspace: Any,
    step: AgentStep,
    *,
    allowed: set[str],
    timeout_seconds: float,
) -> ToolResult:
    if step.tool == "read":
        return tool_read_file(workspace, str(step.arguments.get("path") or ""))
    if step.tool == "grep":
        pattern = str(step.arguments.get("pattern") or "")
        paths = step.arguments.get("paths")
        path_tuple = tuple(paths) if isinstance(paths, list) else None
        return tool_grep(workspace, pattern, paths=path_tuple)
    if step.tool == "write":
        return tool_write_file(
            workspace,
            str(step.arguments.get("path") or ""),
            str(step.arguments.get("content") or ""),
            allowed_paths=allowed,
        )
    if step.tool == "shell":
        cmd = str(step.arguments.get("command") or "")
        args = step.arguments.get("args")
        arg_list = [str(a) for a in args] if isinstance(args, list) else None
        return tool_run_shell(workspace, cmd, arg_list, timeout_seconds=timeout_seconds)
    return ToolResult(step.tool, False, f"unknown tool: {step.tool}")


def _steps_from_llm(
    *,
    workspace: Any,
    plan: SlicePlan,
    base_url: str,
    model_id: str,
    timeout_seconds: float,
    system_prompt: str | None,
) -> list[AgentStep]:
    from hermes_orchestrator.ollama_chat import ollama_chat_json

    context = _gather_context(workspace, plan)
    schema = (
        '{"steps":[{"tool":"read|grep|write|shell","path":"...","content":"...",'
        '"pattern":"...","command":"pytest","args":["..."]}]}'
    )
    system = (
        f"{system_prompt or 'You are a careful coding agent.'}\n"
        f"Implement slice {plan.slice_id} using ONLY allowlisted tools.\n"
        f"Reply with JSON: {schema}. "
        f"Writes must use paths from: {list(plan.target_paths)}. "
        "Prefer small edits; use shell only for pytest or ruff."
    )
    user = (
        f"Rationale: {plan.rationale}\n"
        f"Acceptance: {plan.acceptance_criteria}\n\n"
        f"Workspace context:\n{context}"
    )
    data = ollama_chat_json(
        base_url=base_url,
        model=model_id,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        timeout_seconds=timeout_seconds,
    )
    return _parse_steps(data)


def _default_stub_steps(plan: SlicePlan) -> list[AgentStep]:
    steps: list[AgentStep] = []
    for rel in plan.target_paths[:3]:
        steps.append(AgentStep("read", {"path": rel}))
    return steps


def execute_slice_implement_agent(
    workspace: Any,
    plan: SlicePlan,
    *,
    timeout_seconds: float = 120.0,
    llm_base_url: str | None = None,
    llm_model_id: str | None = None,
    llm_system_prompt: str | None = None,
) -> SliceImplementResult:
    ws = Path(workspace).resolve()
    allowed = _allowed_paths(plan)
    logs: list[str] = []
    touched: list[str] = []

    steps: list[AgentStep] = []
    use_llm = (
        llm_base_url
        and llm_model_id
        and os.environ.get("HERMES_USE_LLM", "").lower() in ("1", "true", "yes")
    )
    if use_llm:
        try:
            steps = _steps_from_llm(
                workspace=ws,
                plan=plan,
                base_url=llm_base_url,
                model_id=llm_model_id,
                timeout_seconds=timeout_seconds,
                system_prompt=llm_system_prompt,
            )
        except Exception as exc:  # noqa: BLE001
            logs.append(f"agent LLM steps failed: {exc}")
            steps = []

    if not steps and use_llm:
        from hermes_orchestrator.llm_slice import execute_slice_implement_llm

        edits = execute_slice_implement_llm(
            plan=plan,
            workspace=ws,
            base_url=llm_base_url,
            model_id=llm_model_id,
            timeout_seconds=timeout_seconds,
            system_prompt=llm_system_prompt,
        )
        if edits:
            steps = [
                AgentStep("write", {"path": e["path"], "content": e["content"]}) for e in edits
            ]

    if not steps:
        steps = _default_stub_steps(plan)

    exit_code = 0
    for step in steps:
        if step.tool == "write":
            rel = str(step.arguments.get("path") or "")
            edits = [{"path": rel, "content": str(step.arguments.get("content") or "")}]
            applied, errors = apply_slice_file_edits(ws, plan, edits)
            touched.extend(applied)
            if errors:
                logs.append("; ".join(errors))
                exit_code = 1
            else:
                logs.append(f"write {rel}")
            continue
        result = _execute_step(ws, step, allowed=allowed, timeout_seconds=timeout_seconds)
        logs.append(f"{result.tool}: {result.output[:500]}")
        if not result.ok:
            exit_code = max(exit_code, 1)

    if not touched and use_llm is False:
        from hermes_orchestrator.slice_implement import execute_slice_implement

        return execute_slice_implement(
            ws,
            plan,
            timeout_seconds=timeout_seconds,
        )

    return SliceImplementResult(
        mode="agent",
        exit_code=exit_code,
        log="\n".join(logs) + "\n",
        paths_touched=tuple(dict.fromkeys(touched)),
    )
