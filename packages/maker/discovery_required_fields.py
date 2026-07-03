from __future__ import annotations

from typing import Any

OPTIONAL_DISCOVERY_QUESTIONS: dict[str, str] = {
    "data_residency": "Any data residency requirement (region, sovereign cloud, or none)?",
}


def discovery_answers_from_requirements(requirements: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(requirements, dict):
        return {}
    scope = requirements.get("scope_discovery")
    if not isinstance(scope, dict):
        return {}
    answers = scope.get("answers")
    if not isinstance(answers, dict):
        return {}
    return {str(k): str(v) for k, v in answers.items() if str(v).strip()}


def missing_required_discovery_fields(
    answers: dict[str, str],
    required_fields: tuple[str, ...] | list[str],
) -> list[str]:
    missing: list[str] = []
    for field_id in required_fields:
        fid = str(field_id).strip()
        if not fid:
            continue
        if not str(answers.get(fid) or "").strip():
            missing.append(fid)
    return missing


def questions_for_required_fields(
    required_fields: tuple[str, ...] | list[str],
) -> list[dict[str, str]]:
    from maker.scope_discovery import SCOPE_QUESTIONS

    known = {q["id"]: q["question"] for q in SCOPE_QUESTIONS}
    out: list[dict[str, str]] = []
    for field_id in required_fields:
        fid = str(field_id).strip()
        if not fid:
            continue
        question = known.get(fid) or OPTIONAL_DISCOVERY_QUESTIONS.get(fid)
        if question:
            out.append({"id": fid, "question": question})
    return out
