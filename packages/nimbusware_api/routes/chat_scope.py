from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from nimbusware_env.env_flags import env_str
from nimbusware_maker.archetype_surface_defaults import manifest_for_archetype
from nimbusware_maker.autopilot_defer_matrix import autopilot_may_auto_defer
from nimbusware_maker.scope_discovery import (
    recommend_for_me,
    scope_confirm,
    scope_discover,
    scope_gather,
)

router = APIRouter(tags=["maker"])


class ScopeDiscoverBody(BaseModel):
    business_prompt: str = Field(min_length=1, max_length=8000)


class ScopeAnswerBody(BaseModel):
    question_id: str = Field(default="", max_length=80)
    question: str = Field(default="", max_length=500)
    answer: str = Field(default="", max_length=4000)


class ScopeGatherBody(BaseModel):
    state: dict[str, Any]
    answers: list[ScopeAnswerBody] = Field(default_factory=list, max_length=10)
    recommend_for_me: bool = False
    archetype: str | None = Field(default=None, max_length=80)
    trust_score: float | None = Field(default=None, ge=0.0, le=10.0)


class ScopeDiscoverResponse(BaseModel):
    scope: dict[str, Any]


@router.post("/scope/discover", response_model=ScopeDiscoverResponse)
def post_scope_discover(body: ScopeDiscoverBody) -> ScopeDiscoverResponse:
    return ScopeDiscoverResponse(scope=scope_discover(body.business_prompt))


@router.post("/scope/gather", response_model=ScopeDiscoverResponse)
def post_scope_gather(body: ScopeGatherBody) -> ScopeDiscoverResponse:
    setup_bundle = env_str("NIMBUSWARE_SETUP_BUNDLE").strip() or "default"
    may_defer = autopilot_may_auto_defer(
        setup_bundle=setup_bundle,
        archetype=body.archetype,
        trust_score=body.trust_score,
    )
    recommend = body.recommend_for_me
    if recommend and not may_defer:
        recommend = False
    gathered = scope_gather(
        body.state,
        [a.model_dump(mode="json") for a in body.answers],
        recommend_for_me_flag=recommend,
    )
    return ScopeDiscoverResponse(scope=gathered)


class ScopeRecommendBody(BaseModel):
    business_prompt: str = Field(min_length=1, max_length=8000)
    archetype: str | None = Field(default=None, max_length=80)


@router.post("/scope/recommend", response_model=ScopeDiscoverResponse)
def post_scope_recommend(body: ScopeRecommendBody) -> ScopeDiscoverResponse:
    setup_bundle = env_str("NIMBUSWARE_SETUP_BUNDLE").strip() or "default"
    state = scope_discover(body.business_prompt)
    recommended = recommend_for_me(state)
    manifest = manifest_for_archetype(
        setup_bundle=setup_bundle,
        archetype=body.archetype,
    )
    recommended["stack_manifest"] = manifest
    from nimbusware_maker.scope_discovery import attach_discovery_summary

    return ScopeDiscoverResponse(scope=attach_discovery_summary(recommended))


class ScopeConfirmBody(BaseModel):
    state: dict[str, Any]


@router.post("/scope/confirm", response_model=ScopeDiscoverResponse)
def post_scope_confirm(body: ScopeConfirmBody) -> ScopeDiscoverResponse:
    try:
        confirmed = scope_confirm(body.state)
    except ValueError as exc:
        from fastapi import HTTPException

        from nimbusware_api.errors import problem

        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    return ScopeDiscoverResponse(scope=confirmed)
