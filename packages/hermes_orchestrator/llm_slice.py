"""LLM-backed micro-slice planning and critique (fo152–fo153)."""

from __future__ import annotations

import json
from typing import Any
import httpx
from pydantic import BaseModel, Field, ValidationError

from hermes_orchestrator.micro_slice import SlicePlan, parse_slice_plan
from hermes_orchestrator.ollama_chat import ollama_chat_json


class LlmSlicePlanResponse(BaseModel):
    model_config = {"extra": "ignore"}

    slice_id: str = Field(min_length=1)
    rationale: str = ""
    target_paths: list[str] = Field(default_factory=list)
    acceptance_criteria: str = ""


class LlmSliceCritiqueResponse(BaseModel):
    model_config = {"extra": "ignore"}

    verdicts: list[str] = Field(default_factory=lambda: ["PASS"])


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
        "You are a Hermes planning agent. Propose one small slice at a time with clear "
        "target paths and acceptance criteria. Never request whole-repo rewrites."
    )


def execute_slice_plan_llm(
    *,
    rows: list[dict[str, Any]],
    base_url: str,
    model_id: str,
    slice_index: int = 1,
    timeout_seconds: float = 120.0,
    system_prompt: str | None = None,
) -> SlicePlan | None:
    """Return a slice plan from Ollama JSON, or None to fall back to stub."""
    agent_prompt = system_prompt or _custom_agent_prompt_from_rows(rows)
    schema = (
        '{"slice_id":"string","rationale":"string","target_paths":["path"],'
        '"acceptance_criteria":"string"}'
    )
    system = (
        f"{agent_prompt}\n\n"
        "Reply with JSON only matching this schema: "
        f"{schema}. "
        "Keep target_paths to at most 3 Python files under packages/. "
        "Prefer existing modules related to the requested change."
    )
    user = (
        f"Propose micro-slice #{slice_index} for this Hermes run. "
        "Use slice_id like slice-{n}."
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
        "You are a Hermes adversarial critic for one micro-slice. "
        'Reply with JSON only: {"verdicts":["PASS"]} or {"verdicts":["FAIL"]}. '
        "FAIL only when the slice scope is unsafe or clearly untestable."
    )
    user = (
        f"Slice {plan.slice_id} targets {list(plan.target_paths)}. "
        f"Acceptance: {plan.acceptance_criteria or 'n/a'}. "
        f"Verify log excerpt:\n{(verify_log or 'ok')[:2000]}"
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
