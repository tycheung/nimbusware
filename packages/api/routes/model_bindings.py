from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.deps import OrchDep
from api.errors import problem
from api.schemas.model_bindings import UserDefaultsBody
from api.schemas.peel_responses import long_tail_json_openapi_responses, with_long_tail_peel_503
from api.user import UserDep
from config.model_bindings_store import (
    list_binding_role_catalog,
    load_user_defaults,
    merge_role_bindings,
    save_user_defaults,
)
from config.store import PostgresConfigStore
from env.env_flags import nimbusware_database_url
from orchestrator.model_routing.preflight import build_binding_preflight_report
from orchestrator.provider_registry import load_provider_presets

router = APIRouter(tags=["platform"])


class ModelBindingsPreflightResponse(BaseModel):
    """GET /platform/model-bindings/preflight (`sak446-b`)."""

    ok: bool | None = None
    roles: list[dict[str, Any]] | None = None
    roles_total: int | None = None
    roles_covered: int | None = None
    roles_without_provider: list[str] | None = None
    providers_reachable: dict[str, Any] | None = None
    inference_mode: str | None = None
    inference_mode_label: str | None = None
    ollama_required: bool | None = None
    issues: list[dict[str, Any]] | None = None
    workflow_profile: str | None = None
    work_type: str | None = None
    surface_stage_map: dict[str, str] | None = None
    stack_manifest_surfaces: list[str] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class ModelBindingsDefaultsResponse(BaseModel):
    """GET/PUT /platform/model-bindings/defaults (`sak446-b`)."""

    defaults: dict[str, Any] | None = None
    roles: list[dict[str, Any]] | None = None
    providers: list[dict[str, Any]] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class ModelBindingsRolesResponse(BaseModel):
    """GET /platform/model-bindings/roles (`sak446-b`)."""

    roles: list[dict[str, Any]] = Field(default_factory=list)


def _config_store() -> PostgresConfigStore | None:
    url = nimbusware_database_url()
    if not url:
        return None
    return PostgresConfigStore(url)


@router.get(
    "/platform/model-bindings/preflight",
    response_model=ModelBindingsPreflightResponse,
    response_model_exclude_none=True,
    summary="Model bindings preflight (`sak446-b`)",
    responses=long_tail_json_openapi_responses(),  # sak501-h
)
def get_model_bindings_preflight(
    orch: OrchDep,
    _: UserDep,
    workflow_profile: Annotated[str | None, Query()] = None,
    work_type: Annotated[str | None, Query()] = None,
    probe: Annotated[bool, Query()] = True,
) -> dict[str, Any]:
    mat = getattr(orch, "_config_materializer", None)
    return build_binding_preflight_report(
        orch.repo_root,
        workflow_profile=workflow_profile,
        work_type=work_type,
        materializer=mat,
        probe=probe,
    )


@router.get(
    "/platform/model-bindings/defaults",
    response_model=ModelBindingsDefaultsResponse,
    response_model_exclude_none=True,
    summary="Model binding defaults (`sak446-b`)",
    responses=long_tail_json_openapi_responses(),  # sak501-h
)
def get_model_binding_defaults(orch: OrchDep, _: UserDep) -> dict[str, Any]:
    store = _config_store()
    doc = load_user_defaults(orch.repo_root, store=store)
    return {
        "defaults": doc,
        "roles": merge_role_bindings(orch.repo_root, store=store),
        "providers": load_provider_presets(orch.repo_root),
    }


@router.put(
    "/platform/model-bindings/defaults",
    response_model=ModelBindingsDefaultsResponse,
    response_model_exclude_none=True,
    summary="Update model binding defaults (`sak446-b`)",
    responses=with_long_tail_peel_503(),  # sak510-i
)
def put_model_binding_defaults(
    body: UserDefaultsBody,
    orch: OrchDep,
    _: UserDep,
) -> dict[str, Any]:
    store = _config_store()
    try:
        doc = save_user_defaults(
            orch.repo_root,
            body.model_dump(mode="json"),
            store=store,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_binding_defaults", str(exc)),
        ) from exc
    return {"defaults": doc}


@router.get(
    "/platform/model-bindings/roles",
    response_model=ModelBindingsRolesResponse,
    response_model_exclude_none=True,
    summary="Model binding role catalog (`sak446-b`)",
    responses=with_long_tail_peel_503(),  # sak510-i
)
def get_model_binding_roles(orch: OrchDep, _: UserDep) -> dict[str, Any]:
    return {"roles": list_binding_role_catalog(orch.repo_root)}
