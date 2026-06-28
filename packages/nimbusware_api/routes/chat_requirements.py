from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from nimbusware_api.errors import problem
from nimbusware_api.routes.runs.create import RunRequirementsBody
from nimbusware_maker.intent import build_requirements_artifact
from nimbusware_maker.scope_discovery import (
    attach_scope_to_requirements,
    discovery_complete_for_start,
    scope_discover,
)
from nimbusware_maker.scope_discovery import (
    recommend_for_me as scope_recommend_for_me,
)


def build_requirements_from_body(requirements: RunRequirementsBody) -> dict[str, Any]:
    artifact = build_requirements_artifact(
        business_prompt=requirements.business_prompt,
        clarifications=[c.model_dump(mode="json") for c in requirements.clarifications],
        scope_discovery=requirements.scope_discovery,
        recommend_for_me=requirements.recommend_for_me,
        stack_manifest=requirements.stack_manifest,
        solo_discipline=requirements.solo_discipline,
    )
    if requirements.recommend_for_me and not requirements.scope_discovery:
        state = scope_discover(requirements.business_prompt)
        state = scope_recommend_for_me(state)
        artifact = attach_scope_to_requirements(artifact, state)
    return artifact


def enforce_discovery_gate(
    requirements: dict[str, Any] | None,
    *,
    workflow_profile: str,
    tenant_slug: str | None = None,
    setup_bundle: str | None = None,
) -> None:
    from nimbusware_env.env_flags import env_str
    from nimbusware_iam.context import get_auth_context

    ctx = get_auth_context()
    slug = tenant_slug or (ctx.tenant_slug if ctx is not None else None)
    bundle = setup_bundle or env_str("NIMBUSWARE_SETUP_BUNDLE").strip() or "default"
    ok, detail = discovery_complete_for_start(
        requirements,
        workflow_profile=workflow_profile,
        tenant_slug=slug,
        setup_bundle=bundle,
    )
    if ok:
        return
    raise HTTPException(
        status_code=422,
        detail=problem(
            "discovery_incomplete",
            detail or "Complete scope discovery before starting a full-stack campaign",
        ),
    )
