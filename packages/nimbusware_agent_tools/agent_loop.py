"""Multi-turn JIT tool loop for slice implement agent mode."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent_core.context_budget import truncate_for_llm_history
from nimbusware_agent_tools.prompts import build_agent_stable_prompt
from nimbusware_agent_tools.risk_caps import AgentRiskCaps
from nimbusware_agent_tools.runtime import AgentStep, _allowed_paths, _execute_step
from nimbusware_agent_tools.tool_registry import agent_tool_list_prompt, is_agent_tool_enabled
from nimbusware_orchestrator.micro_slice import SlicePlan
from nimbusware_orchestrator.prompt_tiers import assemble_prompt

ChatFn = Callable[..., dict[str, Any]]


@dataclass
class AgentLoopResult:
    logs: list[str] = field(default_factory=list)
    paths_touched: list[str] = field(default_factory=list)
    exit_code: int = 0
    tool_steps: int = 0


def _stable_system_prompt(*, base_prompt: str | None, tool_list: str | None = None) -> str:
    listed = tool_list or agent_tool_list_prompt()
    return build_agent_stable_prompt(base_prompt=base_prompt, tool_list=listed)


def _volatile_user_prompt(
    plan: SlicePlan,
    *,
    handoff_summary: str = "",
    memory_excerpt: str = "",
) -> str:
    parts = [
        f"Slice: {plan.slice_id}",
        f"Target paths: {list(plan.target_paths)}",
        f"Rationale: {plan.rationale}",
        f"Acceptance: {plan.acceptance_criteria or 'tests pass'}",
    ]
    if handoff_summary.strip():
        parts.append(f"Prior handoff:\n{handoff_summary}")
    if memory_excerpt.strip():
        parts.append(f"Memory (advisory):\n{truncate_for_llm_history(memory_excerpt)}")
    parts.append("Use tools to inspect and change files. Do not assume file contents.")
    return "\n\n".join(parts)


def _parse_turn(data: dict[str, Any]) -> tuple[bool, list[AgentStep]]:
    if bool(data.get("done")):
        return True, []
    calls = data.get("tool_calls")
    if not isinstance(calls, list):
        steps_raw = data.get("steps")
        if isinstance(steps_raw, list):
            calls = steps_raw
        else:
            return False, []
    steps: list[AgentStep] = []
    for item in calls:
        if not isinstance(item, dict):
            continue
        tool = str(item.get("tool") or "").strip().lower()
        if tool:
            steps.append(AgentStep(tool=tool, arguments=dict(item)))
    return False, steps


def _append_tool_result(
    messages: list[dict[str, str]],
    *,
    tool: str,
    output: str,
    ok: bool,
) -> None:
    bounded = truncate_for_llm_history(output)
    messages.append(
        {
            "role": "user",
            "content": f"Tool {tool} ({'ok' if ok else 'error'}):\n{bounded}",
        },
    )


def run(
    workspace: Path,
    plan: SlicePlan,
    *,
    base_url: str,
    model_id: str,
    timeout_seconds: float = 120.0,
    system_prompt: str | None = None,
    risk_caps: AgentRiskCaps | None = None,
    handoff_summary: str = "",
    memory_excerpt: str = "",
    chat_fn: ChatFn | None = None,
) -> AgentLoopResult:
    from nimbusware_agent_tools.risk_caps import resolve_agent_risk_caps
    from nimbusware_orchestrator.ollama_chat import ollama_chat_json

    ws = workspace.resolve()
    allowed = _allowed_paths(plan)
    caps = risk_caps or resolve_agent_risk_caps()
    chat = chat_fn or ollama_chat_json

    messages = assemble_prompt(
        stable=_stable_system_prompt(base_prompt=system_prompt),
        volatile=_volatile_user_prompt(
            plan,
            handoff_summary=handoff_summary,
            memory_excerpt=memory_excerpt,
        ),
    )

    result = AgentLoopResult()
    shell_invocations = 0
    write_bytes = 0
    touched: list[str] = []

    while True:
        try:
            data = chat(
                base_url=base_url,
                model=model_id,
                messages=messages,
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            result.logs.append(f"agent loop LLM failed: {exc}")
            result.exit_code = 1
            break

        if not isinstance(data, dict):
            result.logs.append("agent loop: invalid LLM response")
            result.exit_code = 1
            break

        done, steps = _parse_turn(data)
        summary = str(data.get("summary") or "").strip()
        if summary:
            result.logs.append(f"agent: {summary[:500]}")
        if done or not steps:
            break

        for step in steps:
            if not is_agent_tool_enabled(step.tool):
                result.logs.append(f"{step.tool}: tool not in allowlist")
                result.exit_code = max(result.exit_code, 1)
                continue
            result.tool_steps += 1
            if result.tool_steps > caps.max_tool_steps:
                result.logs.append(f"risk cap: max_tool_steps={caps.max_tool_steps}")
                result.exit_code = 1
                result.paths_touched = list(dict.fromkeys(touched))
                return result

            if step.tool == "edit":
                old_text = str(step.arguments.get("old_text") or "")
                new_text = str(step.arguments.get("new_text") or "")
                write_bytes += abs(len(new_text.encode("utf-8")) - len(old_text.encode("utf-8")))
            elif step.tool == "write":
                write_bytes += len(str(step.arguments.get("content") or "").encode("utf-8"))

            if write_bytes > caps.max_write_bytes:
                result.logs.append(f"risk cap: max_write_bytes={caps.max_write_bytes}")
                result.exit_code = 1
                result.paths_touched = list(dict.fromkeys(touched))
                return result

            if step.tool == "shell":
                shell_invocations += 1
                if shell_invocations > caps.max_shell_invocations:
                    result.logs.append(
                        f"risk cap: max_shell_invocations={caps.max_shell_invocations}",
                    )
                    result.exit_code = 1
                    result.paths_touched = list(dict.fromkeys(touched))
                    return result

            if step.tool == "write":
                from nimbusware_agent_tools.tools import tool_write_file
                from nimbusware_orchestrator.slice_patch_apply import apply_slice_file_edits

                rel = str(step.arguments.get("path") or "")
                content = str(step.arguments.get("content") or "")
                tool_result = tool_write_file(
                    ws,
                    rel,
                    content,
                    allowed_paths=allowed,
                )
                if tool_result.ok:
                    applied, errors = apply_slice_file_edits(
                        ws,
                        plan,
                        [{"path": rel, "content": content}],
                    )
                    touched.extend(applied)
                    if errors:
                        from nimbusware_agent_tools.tools import _result

                        tool_result = _result(
                            tool_result.tool,
                            False,
                            "; ".join(errors),
                        )
            elif step.tool == "edit":
                from nimbusware_agent_tools.tools import tool_edit_file

                rel = str(step.arguments.get("path") or "")
                tool_result = tool_edit_file(
                    ws,
                    rel,
                    str(step.arguments.get("old_text") or ""),
                    str(step.arguments.get("new_text") or ""),
                    allowed_paths=allowed,
                    replace_all=bool(step.arguments.get("replace_all")),
                )
                if tool_result.ok:
                    touched.append(rel.replace("\\", "/").lstrip("/"))
            else:
                tool_result = _execute_step(
                    ws,
                    step,
                    allowed=allowed,
                    timeout_seconds=timeout_seconds,
                )

            result.logs.append(f"{tool_result.tool}: {tool_result.audit_output[:500]}")
            if not tool_result.ok:
                result.exit_code = max(result.exit_code, 1)

            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {"tool": step.tool, "arguments": step.arguments},
                    ),
                },
            )
            _append_tool_result(
                messages,
                tool=tool_result.tool,
                output=tool_result.llm_output,
                ok=tool_result.ok,
            )

    result.paths_touched = list(dict.fromkeys(touched))
    return result
