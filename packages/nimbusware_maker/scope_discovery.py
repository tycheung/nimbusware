from __future__ import annotations

from copy import deepcopy
from typing import Any

from nimbusware_maker.archetype_surface_defaults import apply_fleet_surface_policy

SCOPE_QUESTIONS: tuple[dict[str, str], ...] = (
    {
        "id": "client_form",
        "question": "Which client should we build first (web app, mobile, or both)?",
    },
    {
        "id": "backend_stack",
        "question": "Any backend stack preference (Python/FastAPI, Node, Go, or no preference)?",
    },
    {
        "id": "frontend_stack",
        "question": "Any frontend preference (React, Vue, or no preference)?",
    },
    {
        "id": "hosting",
        "question": "Where should this run (local only, cloud, or decide later)?",
    },
)

_SCOPE_NARROW_PHRASES = (
    "backend only",
    "api only",
    "rest api only",
    "no frontend",
    "no ui",
    "python only",
    "backend-only",
    "api-only",
)

DEFAULT_MANIFEST: dict[str, Any] = {
    "surfaces": ["api", "web"],
    "stacks": {"api": "fastapi_python", "web": "react_vite"},
    "hosting": "local",
    "recommended": True,
}

BACKEND_ONLY_MANIFEST: dict[str, Any] = {
    "surfaces": ["api"],
    "stacks": {"api": "fastapi_python"},
    "scope_narrowed": True,
    "hosting": "local",
}


def scope_narrowed_to_backend_only(text: str) -> bool:
    low = text.strip().lower()
    return any(phrase in low for phrase in _SCOPE_NARROW_PHRASES)


def scope_analyze(business_prompt: str) -> dict[str, Any]:
    prompt = business_prompt.strip()
    narrowed = scope_narrowed_to_backend_only(prompt)
    if narrowed:
        return {
            "business_prompt": prompt,
            "scope_narrowed": True,
            "surfaces_likely": ["api"],
            "preferences_missing": False,
            "stack_manifest": deepcopy(BACKEND_ONLY_MANIFEST),
        }
    return {
        "business_prompt": prompt,
        "scope_narrowed": False,
        "surfaces_likely": ["api", "web"],
        "preferences_missing": True,
        "stack_manifest": None,
    }


def scope_discover(business_prompt: str) -> dict[str, Any]:
    analysis = scope_analyze(business_prompt)
    if analysis["scope_narrowed"]:
        return {
            **analysis,
            "discovery_complete": True,
            "questions_emitted": [],
            "answers": {},
        }
    return {
        **analysis,
        "discovery_complete": False,
        "questions_emitted": [dict(q) for q in SCOPE_QUESTIONS],
        "answers": {},
    }


def recommend_for_me(
    state: dict[str, Any] | None = None,
    *,
    setup_bundle: str = "default",
    archetype: str | None = None,
    fleet_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from nimbusware_maker.archetype_surface_defaults import manifest_for_archetype

    base = dict(state or {})
    manifest = manifest_for_archetype(
        setup_bundle=setup_bundle,
        archetype=archetype,
        fleet_policy=fleet_policy,
    )
    base["stack_manifest"] = manifest
    base["discovery_complete"] = True
    base["recommend_for_me"] = True
    answers = dict(base.get("answers") or {})
    answers["stack_defer"] = "recommend for me"
    base["answers"] = answers
    return base


def _is_recommend_answer(answers: dict[str, str]) -> bool:
    for key in ("stack_defer", "frontend_stack", "backend_stack", "client_form"):
        val = str(answers.get(key) or "").lower()
        if any(token in val for token in ("recommend", "you pick", "no preference", "defer")):
            return True
    return False


def _answers_sufficient(answers: dict[str, str]) -> bool:
    if _is_recommend_answer(answers):
        return True
    return bool(str(answers.get("client_form") or "").strip())


def _manifest_from_answers(answers: dict[str, str]) -> dict[str, Any]:
    if _is_recommend_answer(answers):
        return deepcopy(DEFAULT_MANIFEST)
    client = str(answers.get("client_form") or "").lower()
    surfaces = ["api"]
    if "web" in client or "both" in client or "mobile" in client:
        surfaces.append("web")
    backend = str(answers.get("backend_stack") or "").lower()
    frontend = str(answers.get("frontend_stack") or "").lower()
    stacks: dict[str, str] = {"api": "fastapi_python"}
    if "node" in backend or "express" in backend:
        stacks["api"] = "node_express"
    if "web" in surfaces:
        stacks["web"] = "react_vite"
        if "vue" in frontend:
            stacks["web"] = "vue_vite"
    hosting = str(answers.get("hosting") or "local").strip() or "local"
    manifest = {
        "surfaces": surfaces,
        "stacks": stacks,
        "hosting": hosting,
        "recommended": False,
    }
    return apply_fleet_surface_policy(manifest, None)


def scope_gather(
    state: dict[str, Any],
    answers: list[dict[str, str]] | None = None,
    *,
    recommend_for_me_flag: bool = False,
) -> dict[str, Any]:
    out = deepcopy(state)
    merged = dict(out.get("answers") or {})
    for raw in answers or []:
        if not isinstance(raw, dict):
            continue
        qid = str(raw.get("question_id") or raw.get("id") or "").strip()
        ans = str(raw.get("answer") or "").strip()
        if qid and ans:
            merged[qid] = ans
    out["answers"] = merged

    if recommend_for_me_flag or _is_recommend_answer(merged):
        return recommend_for_me(out)

    if out.get("scope_narrowed"):
        out["discovery_complete"] = True
        out["stack_manifest"] = deepcopy(BACKEND_ONLY_MANIFEST)
        return out

    if _answers_sufficient(merged):
        out["discovery_complete"] = True
        out["stack_manifest"] = _manifest_from_answers(merged)
    else:
        out["discovery_complete"] = False
        out["stack_manifest"] = None
    return out


def discovery_complete_for_start(
    requirements: dict[str, Any] | None,
    *,
    workflow_profile: str,
) -> tuple[bool, str | None]:
    if workflow_profile != "campaign_fullstack":
        return True, None
    if not isinstance(requirements, dict):
        return False, "requirements required for full-stack campaign"
    if requirements.get("recommend_for_me"):
        return True, None
    scope = requirements.get("scope_discovery")
    if isinstance(scope, dict) and scope.get("discovery_complete"):
        return True, None
    prompt = str(requirements.get("business_prompt") or "")
    if scope_narrowed_to_backend_only(prompt):
        return True, None
    return False, "Complete scope discovery or choose Recommend for me before starting"


def attach_scope_to_requirements(
    requirements: dict[str, Any],
    scope_state: dict[str, Any],
) -> dict[str, Any]:
    out = dict(requirements)
    out["scope_discovery"] = scope_state
    manifest = scope_state.get("stack_manifest")
    if isinstance(manifest, dict):
        out["stack_manifest"] = manifest
    if scope_state.get("recommend_for_me"):
        out["recommend_for_me"] = True
    return out
