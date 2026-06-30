from __future__ import annotations

from copy import deepcopy
from typing import Any

from nimbusware_maker.archetype_surface_defaults import apply_fleet_surface_policy
from nimbusware_maker.archetype_workflow import FULLSTACK_CAMPAIGN_PROFILES

SCOPE_QUESTIONS: tuple[dict[str, str], ...] = (
    {
        "id": "client_form",
        "question": "Which client should we build first (web app, mobile, or both)?",
        "hint": "Web app is the default full-stack path; mobile is deferred to a web-first PWA.",
    },
    {
        "id": "backend_stack",
        "question": "Any backend stack preference (Python/FastAPI, Node, Go, or no preference)?",
        "hint": "FastAPI is the default catalog stack; Node suits existing JS backends.",
    },
    {
        "id": "frontend_stack",
        "question": "Any frontend preference (React, Vue, or no preference)?",
        "hint": "React + Vite is the default; Vue is available when your team prefers it.",
    },
    {
        "id": "hosting",
        "question": "Where should this run (local only, cloud, or decide later)?",
        "hint": "Local only keeps dev env on your machine; cloud unlocks deploy cockpit later.",
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


def scope_discover(
    business_prompt: str,
    *,
    discovery_required_fields: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    from nimbusware_maker.discovery_required_fields import questions_for_required_fields

    analysis = scope_analyze(business_prompt)
    if analysis["scope_narrowed"]:
        return {
            **analysis,
            "discovery_complete": True,
            "questions_emitted": [],
            "answers": {},
        }
    questions = [dict(q) for q in SCOPE_QUESTIONS]
    extra = questions_for_required_fields(discovery_required_fields or ())
    seen = {q["id"] for q in questions}
    for item in extra:
        if item["id"] not in seen:
            questions.append(item)
            seen.add(item["id"])
    return {
        **analysis,
        "discovery_complete": False,
        "questions_emitted": questions,
        "answers": {},
    }


def recommend_for_me(
    state: dict[str, Any] | None = None,
    *,
    setup_bundle: str = "default",
    archetype: str | None = None,
    fleet_policy: dict[str, Any] | None = None,
    tenant_slug: str | None = None,
) -> dict[str, Any]:
    from nimbusware_maker.archetype_surface_defaults import manifest_for_archetype

    base = dict(state or {})
    manifest = manifest_for_archetype(
        setup_bundle=setup_bundle,
        archetype=archetype,
        fleet_policy=fleet_policy,
        tenant_slug=tenant_slug,
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


def _manifest_from_answers(
    answers: dict[str, str],
    *,
    tenant_slug: str | None = None,
) -> dict[str, Any]:
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
    if "cloud" in hosting.lower() or "aws" in hosting.lower():
        manifest["deploy_environment"] = "dev"
    from nimbusware_maker.archetype_surface_defaults import _apply_regulated_stack_guard

    manifest = apply_fleet_surface_policy(manifest, None)
    return _apply_regulated_stack_guard(manifest, tenant_slug)


def scope_gather(
    state: dict[str, Any],
    answers: list[dict[str, str]] | None = None,
    *,
    recommend_for_me_flag: bool = False,
    tenant_slug: str | None = None,
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
        return attach_discovery_summary(
            recommend_for_me(out, tenant_slug=tenant_slug),
        )

    if out.get("scope_narrowed"):
        out["discovery_complete"] = True
        out["stack_manifest"] = deepcopy(BACKEND_ONLY_MANIFEST)
        return attach_discovery_summary(out)

    if _answers_sufficient(merged):
        out["discovery_complete"] = True
        out["stack_manifest"] = _manifest_from_answers(merged, tenant_slug=tenant_slug)
    else:
        out["discovery_complete"] = False
        out["stack_manifest"] = None
    return attach_discovery_summary(out)


def discovery_complete_for_start(
    requirements: dict[str, Any] | None,
    *,
    workflow_profile: str,
    tenant_slug: str | None = None,
    setup_bundle: str | None = None,
) -> tuple[bool, str | None]:
    if workflow_profile not in FULLSTACK_CAMPAIGN_PROFILES:
        return True, None
    if not isinstance(requirements, dict):
        return False, "requirements required for full-stack campaign"
    if requirements.get("recommend_for_me"):
        scope_ok = True
    else:
        scope = requirements.get("scope_discovery")
        if isinstance(scope, dict) and scope.get("discovery_complete"):
            scope_ok = True
        else:
            prompt = str(requirements.get("business_prompt") or "")
            scope_ok = scope_narrowed_to_backend_only(prompt)
    if not scope_ok:
        return False, "Complete scope discovery or choose Recommend for me before starting"

    from nimbusware_env.env_flags import env_str
    from nimbusware_maker.discovery_required_fields import (
        discovery_answers_from_requirements,
        missing_required_discovery_fields,
    )

    bundle = (setup_bundle or env_str("NIMBUSWARE_SETUP_BUNDLE").strip() or "default").lower()
    if bundle != "enterprise":
        return True, None
    from nimbusware_orchestrator.fleet_discovery_policy import tenant_discovery_policy

    policy = tenant_discovery_policy(tenant_slug)
    if not policy.discovery_required_fields:
        return True, None
    answers = discovery_answers_from_requirements(requirements)
    missing = missing_required_discovery_fields(answers, policy.discovery_required_fields)
    if missing:
        joined = ", ".join(missing)
        return False, f"Answer required discovery fields before starting: {joined}"
    return True, None


def scope_confirm(state: dict[str, Any], *, tenant_slug: str | None = None) -> dict[str, Any]:
    from nimbusware_maker.stack_manifest import freeze_manifest, validate_frozen_manifest

    manifest_raw = state.get("stack_manifest")
    if not isinstance(manifest_raw, dict):
        raise ValueError("stack_manifest required")
    answers = state.get("answers") if isinstance(state.get("answers"), dict) else {}
    frozen = freeze_manifest(manifest_raw, answers=answers, confirmed=True)
    errors = validate_frozen_manifest(frozen, tenant_slug=tenant_slug)
    if errors:
        raise ValueError("; ".join(errors))
    out = deepcopy(state)
    out["stack_manifest"] = frozen.model_dump()
    out["scope_confirmed"] = True
    out["discovery_complete"] = True
    try:
        from nimbusware_env import find_repo_root
        from nimbusware_orchestrator.stack_agent_scaffold import scaffold_agents_for_manifest

        agent_ids = scaffold_agents_for_manifest(
            frozen.model_dump(),
            repo_root=find_repo_root(),
            persist=True,
        )
        if agent_ids:
            out["scaffold_agent_ids"] = agent_ids
    except OSError:
        pass
    return out


def attach_discovery_summary(state: dict[str, Any]) -> dict[str, Any]:
    from nimbusware_maker.stack_manifest import discovery_summary_from_answers

    out = deepcopy(state)
    manifest = out.get("stack_manifest")
    if not isinstance(manifest, dict):
        return out
    answers = out.get("answers") if isinstance(out.get("answers"), dict) else {}
    summary = discovery_summary_from_answers(answers)
    if summary:
        manifest = dict(manifest)
        manifest["discovery_summary"] = summary
        out["stack_manifest"] = manifest
    return out


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
