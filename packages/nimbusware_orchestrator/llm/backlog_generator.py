"""LLM-backed delivery backlog generation."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from agent_core.models.backlog import DeliveryBacklog
from nimbusware_orchestrator.ollama_chat import ollama_chat_json


class _LlmBacklogResponse(BaseModel):
    model_config = {"extra": "ignore"}

    backlog: dict[str, Any] = Field(default_factory=dict)


def generate_llm_backlog(
    *,
    campaign_id: str,
    requirements: dict[str, Any] | None,
    base_url: str,
    model_id: str,
    max_slices: int,
    timeout_seconds: float = 120.0,
    repo_context: str = "",
    memory_excerpt: str = "",
) -> DeliveryBacklog | None:
    prompt = _build_prompt(
        requirements=requirements,
        max_slices=max_slices,
        repo_context=repo_context,
        memory_excerpt=memory_excerpt,
    )
    try:
        raw = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You produce a JSON delivery backlog with epics, features, and "
                        "micro-slices. Each slice must have slice_id, target_paths, depends_on, "
                        "estimated_loc, rationale. Keep slices small (<=3 files, <=120 LOC)."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            timeout_seconds=timeout_seconds,
        )
        parsed = _LlmBacklogResponse.model_validate(raw)
        body = dict(parsed.backlog)
        body["campaign_id"] = campaign_id
        return DeliveryBacklog.model_validate(body)
    except (ValidationError, TypeError, ValueError, json.JSONDecodeError, OSError):
        return None


def _build_prompt(
    *,
    requirements: dict[str, Any] | None,
    max_slices: int,
    repo_context: str,
    memory_excerpt: str,
) -> str:
    prompt_text = ""
    if isinstance(requirements, dict):
        prompt_text = str(requirements.get("business_prompt") or "")
    parts = [
        f"Business requirements:\n{prompt_text or '(none)'}",
        f"Max slices: {max_slices}",
        'Return JSON: {"backlog": { ... DeliveryBacklog shape ... }}',
    ]
    if repo_context.strip():
        parts.append(f"Repo map:\n{repo_context[:4000]}")
    if memory_excerpt.strip():
        parts.append(f"Memory excerpts:\n{memory_excerpt[:2000]}")
    return "\n\n".join(parts)
