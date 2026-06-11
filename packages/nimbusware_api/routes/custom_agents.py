from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import OrchDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import (
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
)
from nimbusware_config.persist import load_custom_agent_registry, persist_custom_agent_registry
from nimbusware_extensions.custom_agents import CustomAgent, CustomAgentRegistry

router = APIRouter(prefix="/custom-agents", tags=["custom-agents"])


class CustomAgentResponse(BaseModel):
    id: str
    display_name: str
    system_prompt: str
    description: str = ""
    bound_role_id: str | None = None
    version: int = 1


class CustomAgentListResponse(BaseModel):
    agents: list[CustomAgentResponse]


class CustomAgentUpsertRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    system_prompt: str = Field(min_length=1, max_length=32000)
    description: str = Field(default="", max_length=2000)
    bound_role_id: str | None = Field(default=None, max_length=200)


class CustomAgentCreateRequest(CustomAgentUpsertRequest):
    id: str = Field(min_length=1, max_length=120)


def _config_materializer(orch: Any) -> Any | None:
    return getattr(orch, "config_materializer", None)


def _registry(orch: Any) -> CustomAgentRegistry:
    return load_custom_agent_registry(
        orch.repo_root,
        materializer=_config_materializer(orch),
    )


def _save(registry: CustomAgentRegistry, orch: Any) -> None:
    persist_custom_agent_registry(
        orch.repo_root,
        registry,
        materializer=_config_materializer(orch),
    )


@router.get("", response_model=CustomAgentListResponse)
def list_custom_agents(orch: OrchDep) -> CustomAgentListResponse:
    reg = _registry(orch)
    return CustomAgentListResponse(
        agents=[CustomAgentResponse(**a.to_dict()) for a in reg.list()],
    )


@router.get(
    "/{agent_id}", response_model=CustomAgentResponse, responses={404: PROBLEM_RESPONSE_404}
)
def get_custom_agent(agent_id: str, orch: OrchDep) -> CustomAgentResponse:
    agent = _registry(orch).get(agent_id)
    if agent is None:
        raise HTTPException(
            status_code=404,
            detail=problem("custom_agent_not_found", f"Unknown agent id: {agent_id}"),
        )
    return CustomAgentResponse(**agent.to_dict())


@router.post(
    "",
    response_model=CustomAgentResponse,
    responses={422: PROBLEM_RESPONSE_422, 500: PROBLEM_RESPONSE_500},
)
def create_custom_agent(
    body: CustomAgentCreateRequest,
    orch: OrchDep,
    _admin: AdminDep,
) -> CustomAgentResponse:
    reg = _registry(orch)
    aid = body.id.strip()
    if not aid:
        raise HTTPException(status_code=422, detail=problem("invalid_request", "agent_id required"))
    if reg.get(aid) is not None:
        raise HTTPException(
            status_code=422,
            detail=problem("custom_agent_exists", f"Agent already exists: {aid}"),
        )
    agent = CustomAgent(
        id=aid,
        display_name=body.display_name,
        system_prompt=body.system_prompt,
        description=body.description,
        bound_role_id=body.bound_role_id,
    )
    reg.upsert(agent)
    _save(reg, orch)
    return CustomAgentResponse(**agent.to_dict())


@router.patch(
    "/{agent_id}",
    response_model=CustomAgentResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def update_custom_agent(
    agent_id: str,
    body: CustomAgentUpsertRequest,
    orch: OrchDep,
    _admin: AdminDep,
) -> CustomAgentResponse:
    reg = _registry(orch)
    existing = reg.get(agent_id)
    if existing is None:
        raise HTTPException(
            status_code=404,
            detail=problem("custom_agent_not_found", f"Unknown agent id: {agent_id}"),
        )
    agent = CustomAgent(
        id=agent_id,
        display_name=body.display_name,
        system_prompt=body.system_prompt,
        description=body.description,
        bound_role_id=body.bound_role_id,
        version=existing.version,
    )
    reg.upsert(agent)
    _save(reg, orch)
    saved = reg.get(agent_id)
    assert saved is not None
    return CustomAgentResponse(**saved.to_dict())


@router.delete(
    "/{agent_id}",
    status_code=204,
    responses={404: PROBLEM_RESPONSE_404},
)
def delete_custom_agent(agent_id: str, orch: OrchDep, _admin: AdminDep) -> Response:
    reg = _registry(orch)
    if not reg.remove(agent_id):
        raise HTTPException(
            status_code=404,
            detail=problem("custom_agent_not_found", f"Unknown agent id: {agent_id}"),
        )
    _save(reg, orch)
    return Response(status_code=204)
