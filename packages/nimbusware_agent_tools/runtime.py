from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_core.slice_plan import SlicePlan
from nimbusware_agent_tools.risk_caps import (
    AgentRiskCaps,
    resolve_agent_risk_caps,
)
from nimbusware_agent_tools.tool_registry import is_agent_tool_enabled
from nimbusware_agent_tools.tools import (
    ToolResult,
    tool_edit_file,
    tool_find,
    tool_grep,
    tool_ls,
    tool_read_file,
    tool_run_shell,
    tool_write_file,
)
from nimbusware_env.env_flags import nimbusware_use_llm_enabled
from nimbusware_orchestrator.slice_implement import SliceImplementResult


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
    if not is_agent_tool_enabled(step.tool):
        from nimbusware_agent_tools.tools import _result

        return _result(step.tool, False, f"tool not in allowlist: {step.tool}")
    if step.tool == "read":
        return tool_read_file(workspace, str(step.arguments.get("path") or ""))
    if step.tool == "find":
        pattern = str(step.arguments.get("pattern") or "")
        paths = step.arguments.get("paths")
        path_tuple = tuple(paths) if isinstance(paths, list) else None
        return tool_find(workspace, pattern, paths=path_tuple)
    if step.tool == "ls":
        return tool_ls(workspace, str(step.arguments.get("path") or "."))
    if step.tool == "grep":
        pattern = str(step.arguments.get("pattern") or "")
        paths = step.arguments.get("paths")
        path_tuple = tuple(paths) if isinstance(paths, list) else None
        return tool_grep(workspace, pattern, paths=path_tuple)
    if step.tool == "edit":
        return tool_edit_file(
            workspace,
            str(step.arguments.get("path") or ""),
            str(step.arguments.get("old_text") or ""),
            str(step.arguments.get("new_text") or ""),
            allowed_paths=allowed,
            replace_all=bool(step.arguments.get("replace_all")),
        )
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
    if step.tool == "browser_act":
        from nimbusware_agent_tools.tools import tool_browser_act

        return tool_browser_act(
            base_url=str(step.arguments.get("base_url") or ""),
            action=str(step.arguments.get("action") or "goto"),
            selector=str(step.arguments.get("selector") or "body"),
            value=str(step.arguments.get("value") or ""),
            url=str(step.arguments.get("url") or ""),
        )
    if step.tool == "write_ui_flow":
        from nimbusware_agent_tools.tools import tool_write_ui_flow

        return tool_write_ui_flow(
            workspace,
            str(step.arguments.get("flow_id") or "draft"),
            str(step.arguments.get("yaml") or ""),
        )
    if step.tool == "run_ui_regression":
        from nimbusware_agent_tools.tools import tool_run_ui_regression

        return tool_run_ui_regression(
            workspace,
            base_url=str(step.arguments.get("base_url") or ""),
            flow_id=str(step.arguments.get("flow_id") or ""),
        )
    from nimbusware_agent_tools.tools import _result

    return _result(step.tool, False, f"unknown tool: {step.tool}")


def _steps_from_llm(
    *,
    workspace: Any,
    plan: SlicePlan,
    base_url: str,
    model_id: str,
    timeout_seconds: float,
    system_prompt: str | None,
) -> list[AgentStep]:
    from nimbusware_agent_tools.prompts import build_agent_stable_prompt
    from nimbusware_orchestrator.llm.common import ollama_chat_json_via_plan_patch
    from nimbusware_orchestrator.prompt_tiers import assemble_prompt

    context = _gather_context(workspace, plan)
    schema = (
        '{"steps":[{"tool":"read|grep|edit|write|shell","path":"...","old_text":"...",'
        '"new_text":"...","content":"...","pattern":"...","command":"pytest","args":["..."]}]}'
    )
    stable = build_agent_stable_prompt(
        base_prompt=system_prompt,
        tool_list=f"Reply with JSON: {schema}. Writes must use paths from: {list(plan.target_paths)}.",
    )
    user = (
        f"Rationale: {plan.rationale}\n"
        f"Acceptance: {plan.acceptance_criteria}\n\n"
        f"Workspace context:\n{context}"
    )
    messages = assemble_prompt(stable=stable, volatile=user)
    data = ollama_chat_json_via_plan_patch(
        base_url=base_url,
        model=model_id,
        messages=messages,
        timeout_seconds=timeout_seconds,
        agent_role="backend_writer",
        stage_name="slice.implement",
    )
    return _parse_steps(data)


def _heuristic_grep_token(rationale: str) -> str | None:
    tokens = re.findall(r"[A-Za-z]{4,}", rationale)
    for token in tokens:
        lower = token.lower()
        if lower not in {"slice", "implement", "scaffold", "tests", "verification", "project"}:
            return str(token)
    return None


def _default_heuristic_steps(plan: SlicePlan, workspace: Path) -> list[AgentStep]:
    steps: list[AgentStep] = []
    for rel in plan.target_paths[:3]:
        steps.append(AgentStep("read", {"path": rel}))
    token = _heuristic_grep_token(plan.rationale or "")
    if token:
        search_root = "."
        if plan.target_paths:
            first = str(plan.target_paths[0]).replace("\\", "/")
            search_root = first.rsplit("/", 1)[0] if "/" in first else "."
        steps.append(AgentStep("grep", {"pattern": token, "path": search_root}))
    return steps


def _default_stub_steps(plan: SlicePlan) -> list[AgentStep]:
    return _default_heuristic_steps(plan, Path("."))


def execute_slice_implement_agent(
    workspace: Any,
    plan: SlicePlan,
    *,
    timeout_seconds: float = 120.0,
    llm_base_url: str | None = None,
    llm_model_id: str | None = None,
    llm_system_prompt: str | None = None,
    risk_caps: AgentRiskCaps | None = None,
    learning_excerpt: str = "",
    steer_excerpt: str = "",
) -> SliceImplementResult:
    ws = Path(workspace).resolve()
    allowed = _allowed_paths(plan)
    caps = risk_caps or resolve_agent_risk_caps()
    logs: list[str] = []
    touched: list[str] = []
    tool_steps = 0
    shell_invocations = 0
    write_bytes = 0

    steps: list[AgentStep] = []
    use_llm = llm_base_url is not None and llm_model_id is not None and nimbusware_use_llm_enabled()
    if use_llm and llm_base_url is not None and llm_model_id is not None:
        base_url = llm_base_url
        model_id = llm_model_id
        from nimbusware_env.env_flags import nimbusware_agent_jit_loop_enabled

        if nimbusware_agent_jit_loop_enabled():
            from nimbusware_agent_tools.agent_loop import run as run_agent_loop

            try:
                loop_result = run_agent_loop(
                    ws,
                    plan,
                    base_url=base_url,
                    model_id=model_id,
                    timeout_seconds=timeout_seconds,
                    system_prompt=llm_system_prompt,
                    risk_caps=caps,
                    learning_excerpt=learning_excerpt,
                    steer_excerpt=steer_excerpt,
                )
            except Exception as exc:  # noqa: BLE001
                logs.append(f"agent JIT loop failed: {exc}")
                loop_result = None
            if loop_result is not None and (
                loop_result.exit_code == 0 or loop_result.paths_touched
            ):
                return SliceImplementResult(
                    mode="agent",
                    exit_code=loop_result.exit_code,
                    log="\n".join(loop_result.logs) + "\n",
                    paths_touched=tuple(loop_result.paths_touched),
                )
            if loop_result is not None:
                logs.extend(loop_result.logs)
        try:
            steps = _steps_from_llm(
                workspace=ws,
                plan=plan,
                base_url=base_url,
                model_id=model_id,
                timeout_seconds=timeout_seconds,
                system_prompt=llm_system_prompt,
            )
        except Exception as exc:  # noqa: BLE001
            logs.append(f"agent LLM steps failed: {exc}")
            steps = []

    if not steps and use_llm:
        from nimbusware_orchestrator.llm_slice import execute_slice_implement_llm

        edits = execute_slice_implement_llm(
            plan=plan,
            workspace=ws,
            base_url=base_url,
            model_id=model_id,
            timeout_seconds=timeout_seconds,
            system_prompt=llm_system_prompt,
        )
        if edits:
            steps = [
                AgentStep("write", {"path": e["path"], "content": e["content"]}) for e in edits
            ]

    if not steps:
        steps = _default_heuristic_steps(plan, ws)

    exit_code = 0
    for step in steps:
        tool_steps += 1
        if tool_steps > caps.max_tool_steps:
            logs.append(f"risk cap: max_tool_steps={caps.max_tool_steps}")
            exit_code = max(exit_code, 1)
            break
        if step.tool == "edit":
            rel = str(step.arguments.get("path") or "")
            old_text = str(step.arguments.get("old_text") or "")
            new_text = str(step.arguments.get("new_text") or "")
            delta = abs(len(new_text.encode("utf-8")) - len(old_text.encode("utf-8")))
            write_bytes += delta
            if write_bytes > caps.max_write_bytes:
                logs.append(f"risk cap: max_write_bytes={caps.max_write_bytes}")
                exit_code = max(exit_code, 1)
                break
            result = tool_edit_file(
                ws,
                rel,
                old_text,
                new_text,
                allowed_paths=allowed,
                replace_all=bool(step.arguments.get("replace_all")),
            )
            logs.append(f"{result.tool}: {result.audit_output[:500]}")
            if result.ok:
                touched.append(rel.replace("\\", "/").lstrip("/"))
            else:
                exit_code = max(exit_code, 1)
            continue
        if step.tool == "write":
            rel = str(step.arguments.get("path") or "")
            content = str(step.arguments.get("content") or "")
            write_bytes += len(content.encode("utf-8"))
            if write_bytes > caps.max_write_bytes:
                logs.append(f"risk cap: max_write_bytes={caps.max_write_bytes}")
                exit_code = max(exit_code, 1)
                break
            edits = [{"path": rel, "content": content}]
            from nimbusware_orchestrator.slice_patch_apply import apply_slice_file_edits

            applied, errors = apply_slice_file_edits(ws, plan, edits)
            touched.extend(applied)
            if errors:
                logs.append("; ".join(errors))
                exit_code = 1
            else:
                logs.append(f"write {rel}")
            continue
        if step.tool == "shell":
            shell_invocations += 1
            if shell_invocations > caps.max_shell_invocations:
                logs.append(f"risk cap: max_shell_invocations={caps.max_shell_invocations}")
                exit_code = max(exit_code, 1)
                break
        result = _execute_step(ws, step, allowed=allowed, timeout_seconds=timeout_seconds)
        logs.append(f"{result.tool}: {result.audit_output[:500]}")
        if not result.ok:
            exit_code = max(exit_code, 1)

    if not touched and not use_llm:
        from nimbusware_orchestrator.slice_implement import (
            execute_slice_implement,
            slice_implement_mode,
        )

        if slice_implement_mode() == "agent":
            pass
        else:
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
