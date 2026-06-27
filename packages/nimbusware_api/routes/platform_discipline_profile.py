from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from nimbusware_api.deps import OrchDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep
from nimbusware_api.user import maker_user_id_str
from nimbusware_maker.collab_disciplines import normalize_discipline
from nimbusware_maker.user_discipline_profile import (
    load_user_discipline_profile,
    save_user_discipline_profile,
)
from nimbusware_maker.user_participant_context import (
    load_user_participant_context,
    save_user_participant_context,
)

router = APIRouter(tags=["platform"])


class DisciplineProfileBody(BaseModel):
    default_discipline: str | None = Field(default=None, max_length=32)


class ParticipantContextBody(BaseModel):
    expertise_bullets: list[str] = Field(default_factory=list)


@router.get("/users/me/discipline-profile")
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


@router.put("/users/me/discipline-profile")
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


@router.get("/users/me/participant-context")
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


@router.put("/users/me/participant-context")
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
