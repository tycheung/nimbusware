"""POST /runs create handler."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Header, HTTPException
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

from nimbusware_api.deps import OrchDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import (
    CREATE_RUN_RESPONSE_200,
    CREATE_RUN_RESPONSE_422,
    PROBLEM_RESPONSE_500,
)
from hermes_orchestrator.default_workflow_profile import default_workflow_profile

router = APIRouter()


class CreateRunBody(BaseModel):
    workflow_profile: str = Field(default_factory=default_workflow_profile, min_length=1)
    business_area_persona_id: str | None = Field(default=None, max_length=200)
    development_role_persona_id: str | None = Field(default=None, max_length=200)
    custom_agent_id: str | None = Field(default=None, max_length=120)
    memory_retrieval_enabled: bool | None = Field(default=None)
    memory_index_contribution: bool | None = Field(default=None)


@router.post(
    "/runs",
    responses={
        200: CREATE_RUN_RESPONSE_200,
        422: CREATE_RUN_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def create_run(
    body: CreateRunBody,
    orch: OrchDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    key_uuid: UUID | None = None
    if idempotency_key is not None and str(idempotency_key).strip():
        try:
            key_uuid = UUID(str(idempotency_key).strip())
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=problem(
                    "invalid_request",
                    "Idempotency-Key must be a UUID when set",
                    details={"header": "Idempotency-Key"},
                ),
            ) from exc
    try:
        memory_overrides: dict[str, bool] = {}
        if body.memory_retrieval_enabled is not None:
            memory_overrides["retrieval_enabled"] = body.memory_retrieval_enabled
        if body.memory_index_contribution is not None:
            memory_overrides["index_contribution"] = body.memory_index_contribution
        run_policy_overrides = {"memory": memory_overrides} if memory_overrides else None
        run_id = orch.create_run(
            body.workflow_profile,
            idempotency_key=key_uuid,
            correlation_id=key_uuid,
            business_area_persona_id=body.business_area_persona_id,
            development_role_persona_id=body.development_role_persona_id,
            custom_agent_id=body.custom_agent_id,
            run_policy_overrides=run_policy_overrides,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("workflow_not_found", str(exc)),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("registry_key_error", str(exc)),
        ) from exc
    return {"run_id": str(run_id)}
