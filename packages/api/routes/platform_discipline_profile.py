from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.deps import OrchDep
from api.errors import problem
from api.routes.auth import AuthUserDep
from api.schemas.peel_responses import long_tail_json_openapi_responses, with_long_tail_peel_503
from api.user import maker_user_id_str
from maker.collab.disciplines import normalize_discipline
from maker.user_agent_overlay import (
    load_user_agent_overlays,
    overlay_catalog,
    save_user_agent_overlay,
)
from maker.user_discipline_profile import (
    load_user_discipline_profile,
    save_user_discipline_profile,
)
from maker.user_participant_context import (
    load_user_participant_context,
    save_user_participant_context,
)

router = APIRouter(tags=["platform"])


class DisciplineProfileBody(BaseModel):
    default_discipline: str | None = Field(default=None, max_length=32)


class ParticipantContextBody(BaseModel):
    expertise_bullets: list[str] = Field(default_factory=list)


class AgentOverlayBody(BaseModel):
    custom_agent_id: str | None = Field(default=None, max_length=120)
    prompt_extension: str | None = Field(default=None, max_length=2000)


class DisciplineProfileResponse(BaseModel):
    """GET/PUT /users/me/discipline-profile (`sak483-g`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


class ParticipantContextResponse(BaseModel):
    """GET/PUT /users/me/participant-context (`sak483-g`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


class AgentOverlaysResponse(BaseModel):
    """GET /users/me/agent-overlays (`sak483-g`)."""

    model_config = {"extra": "allow"}

    disciplines: list[dict[str, Any]] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class AgentOverlayResponse(BaseModel):
    """PUT /users/me/agent-overlays/{discipline} (`sak483-g`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/users/me/discipline-profile",
    response_model=DisciplineProfileResponse,
    response_model_exclude_none=True,
    summary="Discipline profile GET (`sak483-g`)",
    responses=long_tail_json_openapi_responses(),  # sak503-b
)
def get_discipline_profile(
    request: Request,
    orch: OrchDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    uid = str(user.user_id) if user is not None else maker_user_id_str(request)
    if not uid:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "user identity required"),
        )
    return load_user_discipline_profile(uid, repo_root=orch.repo_root)


@router.put(
    "/users/me/discipline-profile",
    response_model=DisciplineProfileResponse,
    response_model_exclude_none=True,
    summary="Discipline profile PUT (`sak483-g`)",
    responses=with_long_tail_peel_503(),  # sak516-h
)
def put_discipline_profile(
    body: DisciplineProfileBody,
    request: Request,
    orch: OrchDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    uid = str(user.user_id) if user is not None else maker_user_id_str(request)
    if not uid:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "user identity required"),
        )
    discipline = body.default_discipline
    if discipline is not None and discipline.strip():
        normalized = normalize_discipline(discipline, repo_root=orch.repo_root)
        if normalized is None:
            raise HTTPException(
                status_code=422,
                detail=problem("invalid_request", "unknown discipline"),
            )
        discipline = normalized
    else:
        discipline = None
    try:
        return save_user_discipline_profile(
            uid,
            default_discipline=discipline,
            repo_root=orch.repo_root,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc


@router.get(
    "/users/me/participant-context",
    response_model=ParticipantContextResponse,
    response_model_exclude_none=True,
    summary="Participant context GET (`sak483-g`)",
    responses=with_long_tail_peel_503(),  # sak516-h
)
def get_participant_context(
    request: Request,
    orch: OrchDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    uid = str(user.user_id) if user is not None else maker_user_id_str(request)
    if not uid:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "user identity required"),
        )
    return load_user_participant_context(uid, repo_root=orch.repo_root)


@router.put(
    "/users/me/participant-context",
    response_model=ParticipantContextResponse,
    response_model_exclude_none=True,
    summary="Participant context PUT (`sak483-g`)",
    responses=with_long_tail_peel_503(),  # sak516-i
)
def put_participant_context(
    body: ParticipantContextBody,
    request: Request,
    orch: OrchDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    uid = str(user.user_id) if user is not None else maker_user_id_str(request)
    if not uid:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "user identity required"),
        )
    try:
        return save_user_participant_context(
            uid,
            expertise_bullets=body.expertise_bullets,
            repo_root=orch.repo_root,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc


@router.get(
    "/users/me/agent-overlays",
    response_model=AgentOverlaysResponse,
    response_model_exclude_none=True,
    summary="Agent overlays GET (`sak483-g`)",
    responses=with_long_tail_peel_503(),  # sak516-i
)
def get_agent_overlays(
    request: Request,
    orch: OrchDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    uid = str(user.user_id) if user is not None else maker_user_id_str(request)
    if not uid:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "user identity required"),
        )
    body = load_user_agent_overlays(uid, repo_root=orch.repo_root)
    body["disciplines"] = overlay_catalog(repo_root=orch.repo_root)
    return body


@router.put(
    "/users/me/agent-overlays/{discipline}",
    response_model=AgentOverlayResponse,
    response_model_exclude_none=True,
    summary="Agent overlay PUT (`sak483-g`)",
    responses=with_long_tail_peel_503(),  # sak517-a
)
def put_agent_overlay(
    discipline: str,
    body: AgentOverlayBody,
    request: Request,
    orch: OrchDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    uid = str(user.user_id) if user is not None else maker_user_id_str(request)
    if not uid:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "user identity required"),
        )
    try:
        return save_user_agent_overlay(
            uid,
            discipline,
            custom_agent_id=body.custom_agent_id,
            prompt_extension=body.prompt_extension,
            repo_root=orch.repo_root,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
