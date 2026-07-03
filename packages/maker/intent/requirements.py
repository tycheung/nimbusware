from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from maker.solo_discipline import solo_discipline_routes as build_solo_discipline_routes

CLARIFYING_QUESTIONS: tuple[dict[str, str], ...] = (
    {
        "id": "audience",
        "question": "Who will use this software?",
    },
    {
        "id": "outcome",
        "question": "What should they be able to do when you are done?",
    },
    {
        "id": "must_have",
        "question": "What are the must-have features for the first version?",
    },
    {
        "id": "avoid",
        "question": "What should we explicitly not build yet?",
    },
    {
        "id": "success",
        "question": "How will you know it is working?",
    },
)


def build_requirements_artifact(
    *,
    business_prompt: str,
    clarifications: list[dict[str, str]] | None = None,
    scope_discovery: dict[str, Any] | None = None,
    recommend_for_me: bool = False,
    stack_manifest: dict[str, Any] | None = None,
    solo_discipline: str | None = None,
) -> dict[str, Any]:
    prompt = business_prompt.strip()
    if not prompt:
        raise ValueError("business_prompt required")
    cleaned: list[dict[str, str]] = []
    for raw in clarifications or []:
        if not isinstance(raw, dict):
            continue
        answer = str(raw.get("answer", "")).strip()
        if not answer:
            continue
        qid = str(raw.get("question_id") or raw.get("id") or "").strip()
        question = str(raw.get("question", "")).strip()
        cleaned.append(
            {
                "question_id": qid,
                "question": question,
                "answer": answer,
            },
        )
    artifact: dict[str, Any] = {
        "business_prompt": prompt,
        "clarifications": cleaned,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
    }
    if scope_discovery is not None:
        artifact["scope_discovery"] = scope_discovery
    if recommend_for_me:
        artifact["recommend_for_me"] = True
    if stack_manifest is not None:
        artifact["stack_manifest"] = stack_manifest
    routes = build_solo_discipline_routes(prompt, solo_hat=solo_discipline)
    if routes:
        artifact["solo_discipline_routes"] = routes
    return artifact


def plan_summary_from_requirements(requirements: dict[str, Any] | None) -> str:
    if not isinstance(requirements, dict):
        return "No business intent recorded for this run."
    prompt = str(requirements.get("business_prompt") or "").strip()
    if not prompt:
        return "No business intent recorded for this run."
    parts = [f"You asked for: {prompt[:240]}"]
    clarifications = requirements.get("clarifications")
    if isinstance(clarifications, list):
        for item in clarifications[:3]:
            if not isinstance(item, dict):
                continue
            answer = str(item.get("answer") or "").strip()
            if not answer:
                continue
            question = str(item.get("question") or "Detail").strip()
            parts.append(f"{question}: {answer[:120]}")
    return " ".join(parts)


def requirements_from_run_created_metadata(
    metadata: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(metadata, dict):
        return None
    req = metadata.get("requirements")
    return dict(req) if isinstance(req, dict) else None
