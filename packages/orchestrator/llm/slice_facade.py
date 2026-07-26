"""Slice LLM entrypoints after sak411 llm_slice.py delete — broker or raise."""

from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from agent_core.context_budget import truncate_for_llm_history
from agent_core.prompt_tiers import assemble_prompt, stable_slice_agent_block
from orchestrator.llm.chat_facade import ollama_chat_json_via_plan_patch
from orchestrator.slice.micro_slice import SlicePlan, parse_slice_plan


class LlmSlicePlanResponse(BaseModel):
    model_config = {"extra": "ignore"}

    slice_id: str = Field(min_length=1)
    rationale: str = ""
    target_paths: list[str] = Field(default_factory=list)
    acceptance_criteria: str = ""


def _require_broker_chat(messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    # sak492-d: slice stages are Maker-critical — no silent resolver/ollama fallback.
    return ollama_chat_json_via_plan_patch(
        messages=messages,
        peel_strict=True,
        **kwargs,
    )


def _peel_reraise_or_none() -> None:
    from broker_client.flags import broker_llm_enabled

    if broker_llm_enabled():  # sak497-a
        raise


def _agent_prompt_from_rows(
    rows: list[dict[str, Any]],
    *,
    system_prompt: str | None = None,
) -> str:
    if system_prompt and system_prompt.strip():
        base = system_prompt.strip()
    else:
        base = (
            "You are a Nimbusware planning agent. Propose one small slice at a time with clear "
            "target paths and acceptance criteria. Never request whole-repo rewrites."
        )
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
                    base = str(preview)
            break
    from orchestrator.collab.mesh_context import mesh_agent_overlay_prompt
    from orchestrator.model_routing.audit import active_role_claims_from_events

    claims = active_role_claims_from_events(rows)
    if claims:
        from env import find_repo_root
        from maker.user_agent_overlay import prompt_addon_for_run_claims

        claim_addon = prompt_addon_for_run_claims(claims, repo_root=find_repo_root()).strip()
        if claim_addon and claim_addon not in base:
            base = f"{base}\n\n{claim_addon}"

    mesh_addon = mesh_agent_overlay_prompt().strip()
    if mesh_addon and mesh_addon not in base:
        base = f"{base}\n\n{mesh_addon}"
    return base


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
    agent_prompt = _agent_prompt_from_rows(rows, system_prompt=system_prompt)
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
        data = _require_broker_chat(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
            stage_name="slice.plan",
            agent_role="planner",
        )
        parsed = LlmSlicePlanResponse.model_validate(data)
        return parse_slice_plan(parsed.model_dump())
    except RuntimeError as exc:
        if "broker_miss" in str(exc) or "broker miss" in str(exc):
            _peel_reraise_or_none()
        return None
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        _peel_reraise_or_none()
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
    agent_prompt = _agent_prompt_from_rows(rows, system_prompt=system_prompt)
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
        data = _require_broker_chat(
            base_url=base_url,
            model=model_id,
            messages=messages,
            timeout_seconds=timeout_seconds,
            stage_name="slice.plan",
            agent_role="planner",
        )
        parsed = LlmSlicePlanResponse.model_validate(data)
        return parse_slice_plan(parsed.model_dump())
    except RuntimeError as exc:
        if "broker_miss" in str(exc) or "broker miss" in str(exc):
            _peel_reraise_or_none()
        return None
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        _peel_reraise_or_none()
        return None


def execute_slice_implement_llm(*args: Any, **kwargs: Any) -> Any:
    raise RuntimeError(
        "execute_slice_implement_llm local path removed (sak411); use broker llm bind"
    )


def execute_slice_critique_llm(*args: Any, **kwargs: Any) -> Any:
    raise RuntimeError(
        "execute_slice_critique_llm local path removed (sak411); use broker llm bind"
    )


# Back-compat alias used by overlay / critic pairing tests.
_custom_agent_prompt_from_rows = _agent_prompt_from_rows


__all__ = [
    "execute_slice_critique_llm",
    "execute_slice_implement_llm",
    "execute_slice_plan_llm",
    "execute_slice_replan_llm",
    "_custom_agent_prompt_from_rows",
    "_require_broker_chat",
]
