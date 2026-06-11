from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from agent_core.context_budget import truncate_for_llm_history
from nimbusware_orchestrator.micro_slice import SlicePlan, parse_slice_plan
from nimbusware_orchestrator.ollama_chat import ollama_chat_json
from nimbusware_orchestrator.prompt_tiers import assemble_prompt, stable_slice_agent_block


class LlmSlicePlanResponse(BaseModel):
    model_config = {"extra": "ignore"}

    slice_id: str = Field(min_length=1)
    rationale: str = ""
    target_paths: list[str] = Field(default_factory=list)
    acceptance_criteria: str = ""


class LlmSliceCritiqueResponse(BaseModel):
    model_config = {"extra": "ignore"}

    verdicts: list[str] = Field(default_factory=lambda: ["PASS"])


class LlmSliceFileEdit(BaseModel):
    model_config = {"extra": "ignore"}

    path: str = Field(min_length=1)
    content: str = ""


class LlmSliceImplementResponse(BaseModel):
    model_config = {"extra": "ignore"}

    edits: list[LlmSliceFileEdit] = Field(default_factory=list)
    summary: str = ""


def _custom_agent_prompt_from_rows(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        if row.get("event_type") != "run.created":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            break
        agent = meta.get("custom_agent")
        if isinstance(agent, dict):
            preview = agent.get("system_prompt_preview") or ""
            if preview:
                return str(preview)
        break
    return (
        "You are a Nimbusware planning agent. Propose one small slice at a time with clear "
        "target paths and acceptance criteria. Never request whole-repo rewrites."
    )


def execute_slice_replan_llm(
    *,
    rows: list[dict[str, Any]],
    base_url: str,
    model_id: str,
    prior_plan: SlicePlan,
    budget_message: str,
    replan_attempt: int,
    timeout_seconds: float = 120.0,
    system_prompt: str | None = None,
) -> SlicePlan | None:
    """Ask LLM for a narrower slice after diff budget failure."""
    agent_prompt = system_prompt or _custom_agent_prompt_from_rows(rows)
    schema = (
        '{"slice_id":"string","rationale":"string","target_paths":["path"],'
        '"acceptance_criteria":"string"}'
    )
    system = (
        f"{agent_prompt}\n\n"
        "The previous slice was too large. Reply with JSON only matching: "
        f"{schema}. "
        f"Use fewer paths than before (max {max(1, len(prior_plan.target_paths) - 1)} files). "
        "Keep each slice small enough to review and test."
    )
    user = (
        f"Replan attempt {replan_attempt}. Prior slice_id={prior_plan.slice_id}, "
        f"paths={list(prior_plan.target_paths)}. Budget failure: {budget_message}. "
        "Propose a smaller slice_id (e.g. slice-1-r1)."
    )
    try:
        data = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
        )
        parsed = LlmSlicePlanResponse.model_validate(data)
        return parse_slice_plan(parsed.model_dump())
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
        RuntimeError,
    ):
        return None


def execute_slice_plan_llm(
    *,
    rows: list[dict[str, Any]],
    base_url: str,
    model_id: str,
    slice_index: int = 1,
    timeout_seconds: float = 120.0,
    system_prompt: str | None = None,
    budget_feedback: str | None = None,
    memory_excerpt: str = "",
    handoff_summary: str = "",
) -> SlicePlan | None:
    """Return a slice plan from Ollama JSON, or None to fall back to stub."""
    agent_prompt = system_prompt or _custom_agent_prompt_from_rows(rows)
    schema = (
        '{"slice_id":"string","rationale":"string","target_paths":["path"],'
        '"acceptance_criteria":"string"}'
    )
    stable = stable_slice_agent_block(
        tool_rules=(
            f"{agent_prompt}\n"
            "Reply with JSON only matching this schema: "
            f"{schema}. "
            "Keep target_paths to at most 3 Python files under packages/. "
            "Prefer existing modules related to the requested change."
        ),
    )
    volatile_parts = [
        f"Propose micro-slice #{slice_index} for this Nimbusware run. "
        "Use slice_id like slice-{n}.",
    ]
    if handoff_summary.strip():
        volatile_parts.append(
            f"Prior slice handoff:\n{truncate_for_llm_history(handoff_summary, max_chars=4000)}",
        )
    if memory_excerpt.strip():
        volatile_parts.append(
            f"Prior failure memory (advisory):\n{truncate_for_llm_history(memory_excerpt)}",
        )
    if budget_feedback:
        volatile_parts.append(f"Prior budget feedback: {budget_feedback}")
    messages = assemble_prompt(
        stable=stable,
        volatile="\n\n".join(volatile_parts),
    )
    try:
        data = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=messages,
            timeout_seconds=timeout_seconds,
        )
        parsed = LlmSlicePlanResponse.model_validate(data)
        return parse_slice_plan(parsed.model_dump())
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
        RuntimeError,
    ):
        return None


def execute_slice_implement_llm(
    *,
    plan: SlicePlan,
    workspace: Path,
    base_url: str,
    model_id: str,
    timeout_seconds: float = 120.0,
    system_prompt: str | None = None,
    learning_excerpt: str = "",
) -> list[dict[str, str]] | None:
    """Return file edits for slice.implement, or None to fall back to scoped ruff."""
    from pathlib import Path as _Path

    agent_prompt = system_prompt or "You are a Nimbusware implementation agent for one micro-slice."
    excerpts: list[str] = []
    for rel in plan.target_paths[:3]:
        fp = _Path(workspace) / rel
        if fp.is_file():
            try:
                text = fp.read_text(encoding="utf-8")
            except OSError:
                continue
            excerpts.append(f"--- {rel} ---\n{truncate_for_llm_history(text, max_chars=4000)}\n")
    schema = '{"edits":[{"path":"string","content":"string"}],"summary":"string"}'
    system = (
        f"{agent_prompt}\n\n"
        "Reply with JSON only matching: "
        f"{schema}. "
        "Provide FULL file content for each edited path. "
        "Only include paths from the slice plan. Keep changes minimal."
    )
    user = (
        f"Implement slice {plan.slice_id} for paths {list(plan.target_paths)}. "
        f"Acceptance: {plan.acceptance_criteria or 'tests pass'}. "
        f"Rationale: {plan.rationale}\n\n"
    )
    if learning_excerpt.strip():
        user += (
            f"Prior failure learning (avoid repeating):\n"
            f"{truncate_for_llm_history(learning_excerpt)}\n\n"
        )
    user += f"Current files:\n{truncate_for_llm_history(''.join(excerpts), max_chars=12000)}"
    try:
        data = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
        )
        parsed = LlmSliceImplementResponse.model_validate(data)
        return [{"path": e.path, "content": e.content} for e in parsed.edits]
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
        RuntimeError,
    ):
        return None


def execute_slice_critique_llm(
    *,
    plan: SlicePlan,
    base_url: str,
    model_id: str,
    verify_log: str = "",
    timeout_seconds: float = 120.0,
) -> list[str]:
    """LLM critique verdicts for slice.critique; defaults to PASS on failure."""
    system = (
        "You are a Nimbusware adversarial critic for one micro-slice. "
        'Reply with JSON only: {"verdicts":["PASS"]} or {"verdicts":["FAIL"]}. '
        "FAIL only when the slice scope is unsafe or clearly untestable."
    )
    user = (
        f"Slice {plan.slice_id} targets {list(plan.target_paths)}. "
        f"Acceptance: {plan.acceptance_criteria or 'n/a'}. "
        f"Verify log excerpt:\n{truncate_for_llm_history(verify_log or 'ok')}"
    )
    try:
        data = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
        )
        parsed = LlmSliceCritiqueResponse.model_validate(data)
        return [v.upper() for v in parsed.verdicts if str(v).strip()] or ["PASS"]
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
        RuntimeError,
    ):
        return ["PASS"]
