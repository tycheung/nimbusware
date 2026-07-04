from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent_core.agent_full_compact import maybe_full_compact_messages
from agent_core.context_budget import estimate_tokens, truncate_for_llm_history
from agent_core.prompt_tiers import CacheBreakingSection, assemble_prompt_with_cache_metadata
from agent_core.slice_plan import SlicePlan
from agent_core.tool_output_offload import prepare_tool_output_for_llm
from agent_tools.prompts import build_agent_stable_prompt
from agent_tools.risk_caps import AgentRiskCaps
from agent_tools.runtime import AgentStep, _allowed_paths, _execute_step
from agent_tools.tool_registry import agent_tool_list_prompt, is_agent_tool_enabled

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
    learning_excerpt: str = "",
    steer_excerpt: str = "",
) -> str:
    parts = [
        f"Slice: {plan.slice_id}",
        f"Target paths: {list(plan.target_paths)}",
        f"Rationale: {plan.rationale}",
        f"Acceptance: {plan.acceptance_criteria or 'tests pass'}",
    ]
    if handoff_summary.strip():
        parts.append(f"Prior handoff:\n{handoff_summary}")
    if steer_excerpt.strip():
        parts.append(
            f"Operator steer (follow for this slice):\n{truncate_for_llm_history(steer_excerpt)}",
        )
    if memory_excerpt.strip():
        parts.append(f"Memory (advisory):\n{truncate_for_llm_history(memory_excerpt)}")
    if learning_excerpt.strip():
        parts.append(
            f"Prior failure learning (apply fixes, do not repeat mistakes):\n"
            f"{truncate_for_llm_history(learning_excerpt)}",
        )
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


_MICROCOMPACT_TOOLS = frozenset({"read", "write", "edit", "grep", "shell", "find", "ls"})


@dataclass
class _LoopContext:
    tool_result_indices: list[int] = field(default_factory=list)
    dedup_index: dict[str, int] = field(default_factory=dict)
    turn: int = 0


def _dedup_key(tool: str, arguments: dict[str, Any]) -> str | None:
    from env.env_flags import nimbusware_context_dedup_mode

    mode = nimbusware_context_dedup_mode()
    if mode == "off":
        return None
    t = tool.lower()
    if t in ("read", "write", "edit"):
        path = str(arguments.get("path") or "").strip().replace("\\", "/")
        return f"{t}:{path}" if path else None
    if t == "grep" and mode in ("balanced", "compact"):
        pattern = str(arguments.get("pattern") or arguments.get("query") or "")
        path = str(arguments.get("path") or ".").strip().replace("\\", "/")
        return f"grep:{pattern}:{path}"
    if t == "shell" and mode == "compact":
        cmd = str(arguments.get("command") or arguments.get("cmd") or "")
        if not cmd:
            return None
        digest = hashlib.sha256(cmd.encode("utf-8")).hexdigest()[:16]
        return f"shell:{digest}"
    return None


def _maybe_dedup_tool_messages(
    messages: list[dict[str, str]],
    *,
    ctx: _LoopContext,
    tool: str,
    arguments: dict[str, Any],
) -> None:
    key = _dedup_key(tool, arguments)
    if not key:
        return
    prior = ctx.dedup_index.get(key)
    if prior is not None and 0 <= prior < len(messages):
        messages[prior] = {
            **messages[prior],
            "content": f"[superseded by turn {ctx.turn}]",
        }
    ctx.dedup_index[key] = len(messages) - 1


def _maybe_microcompact_messages(
    messages: list[dict[str, str]],
    *,
    ctx: _LoopContext,
    tool: str,
) -> None:
    if tool not in _MICROCOMPACT_TOOLS:
        return
    from env.env_flags import (
        nimbusware_jit_microcompact_token_threshold,
        nimbusware_jit_microcompact_turns,
    )

    est = sum(estimate_tokens(str(m.get("content") or "")) for m in messages)
    if est < nimbusware_jit_microcompact_token_threshold():
        return
    keep = nimbusware_jit_microcompact_turns()
    if len(ctx.tool_result_indices) <= keep:
        return
    for idx in ctx.tool_result_indices[:-keep]:
        msg = messages[idx]
        if msg.get("role") == "user" and msg.get("content", "").startswith("Tool "):
            messages[idx] = {**msg, "content": "[cleared prior tool result]"}
    ctx.tool_result_indices = ctx.tool_result_indices[-keep:]


def _append_tool_result(
    messages: list[dict[str, str]],
    *,
    tool: str,
    output: str,
    ok: bool,
    workspace: Path | None = None,
    run_id: str = "",
    step: int = 0,
    ctx: _LoopContext | None = None,
) -> None:
    llm_output = output
    if workspace is not None and run_id:
        llm_output, _ = prepare_tool_output_for_llm(
            output,
            workspace=workspace,
            run_id=run_id,
            step=step,
        )
    else:
        llm_output = truncate_for_llm_history(output)
    messages.append(
        {
            "role": "user",
            "content": f"Tool {tool} ({'ok' if ok else 'error'}):\n{llm_output}",
        },
    )
    if ctx is not None:
        ctx.tool_result_indices.append(len(messages) - 1)


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
    learning_excerpt: str = "",
    steer_excerpt: str = "",
    chat_fn: ChatFn | None = None,
) -> AgentLoopResult:
    from agent_tools.risk_caps import resolve_agent_risk_caps
    from orchestrator.llm.common import ollama_chat_json_via_plan_patch

    ws = workspace.resolve()
    allowed = _allowed_paths(plan)
    caps = risk_caps or resolve_agent_risk_caps()

    def _default_chat(**kwargs: Any) -> dict[str, Any]:
        return ollama_chat_json_via_plan_patch(
            **kwargs,
            agent_role="backend_writer",
            stage_name="slice.implement",
        )

    chat = chat_fn or _default_chat

    dynamic: list[CacheBreakingSection] = []
    if steer_excerpt.strip():
        dynamic.append(
            CacheBreakingSection(
                label="operator_steer",
                content=f"Operator steer (follow for this slice):\n{truncate_for_llm_history(steer_excerpt)}",
            ),
        )
    assembled = assemble_prompt_with_cache_metadata(
        stable=_stable_system_prompt(base_prompt=system_prompt),
        volatile=_volatile_user_prompt(
            plan,
            handoff_summary=handoff_summary,
            memory_excerpt=memory_excerpt,
            learning_excerpt=learning_excerpt,
            steer_excerpt="",
        ),
        dynamic_sections=dynamic,
    )
    messages = assembled.messages

    result = AgentLoopResult()
    shell_invocations = 0
    write_bytes = 0
    touched: list[str] = []
    run_id = plan.slice_id or "agent-loop"
    loop_ctx = _LoopContext()

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
            loop_ctx.turn += 1
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

            if step.tool == "browser_act":
                from agent_tools.tools import tool_browser_act

                page_url = str(step.arguments.get("base_url") or "").strip()
                if not page_url:
                    from orchestrator.dev_env.supervisor import active_base_url

                    page_url = active_base_url(ws) or ""
                tool_result = tool_browser_act(
                    base_url=page_url,
                    action=str(step.arguments.get("action") or "goto"),
                    selector=str(step.arguments.get("selector") or "body"),
                    value=str(step.arguments.get("value") or ""),
                    url=str(step.arguments.get("url") or ""),
                )
            elif step.tool == "write":
                from agent_tools.tools import tool_write_file
                from orchestrator.slice.patch_apply import apply_slice_file_edits

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
                        from agent_tools.tools import _result

                        tool_result = _result(
                            tool_result.tool,
                            False,
                            "; ".join(errors),
                        )
            elif step.tool == "edit":
                from agent_tools.tools import tool_edit_file

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
                workspace=ws,
                run_id=run_id,
                step=result.tool_steps,
                ctx=loop_ctx,
            )
            _maybe_microcompact_messages(messages, ctx=loop_ctx, tool=tool_result.tool)
            _maybe_dedup_tool_messages(
                messages,
                ctx=loop_ctx,
                tool=tool_result.tool,
                arguments=step.arguments,
            )
            compacted, _saved = maybe_full_compact_messages(messages)
            if compacted is not messages:
                messages[:] = compacted

    result.paths_touched = list(dict.fromkeys(touched))
    return result
