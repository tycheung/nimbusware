from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.admin import AdminDep
from api.deps import IamStoreDep
from api.errors import problem
from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import enterprise_peel_json_openapi_responses
from iam.constants import DEFAULT_TENANT_ID
from iam.context import get_auth_context
from iam.scopes import DEFAULT_ADMIN_SCOPES, DEFAULT_USER_SCOPES, normalize_scopes

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class TenantCreateBody(BaseModel):
    slug: str = Field(min_length=1, max_length=64)
    display_name: str = Field(default="", max_length=256)


class ApiKeyCreateBody(BaseModel):
    label: str = Field(default="", max_length=128)
    role_taxonomy_keys: list[str] = Field(default_factory=list)
    api_scopes: list[str] = Field(default_factory=lambda: list(DEFAULT_USER_SCOPES))


class IamBootstrapResponse(BaseModel):
    """POST /enterprise/iam/bootstrap (`sak485-g`)."""

    model_config = {"extra": "allow"}

    tenant_id: str | None = None
    tenant_slug: str | None = None
    key_id: str | None = None
    key_prefix: str | None = None
    api_key: str | None = None
    role_taxonomy_keys: list[str] | None = None
    api_scopes: list[str] | None = None
    message: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class IamMeResponse(BaseModel):
    """GET /enterprise/iam/me (`sak485-g`)."""

    model_config = {"extra": "allow"}

    tenant_id: str | None = None
    tenant_slug: str | None = None
    key_id: str | None = None
    role_taxonomy_keys: list[str] | None = None
    api_scopes: list[str] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class TenantsListResponse(BaseModel):
    """GET /enterprise/tenants (`sak485-g`)."""

    model_config = {"extra": "allow"}

    tenants: list[dict[str, Any]] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class TenantCreateResponse(BaseModel):
    """POST /enterprise/tenants (`sak485-g`)."""

    model_config = {"extra": "allow"}

    tenant_id: str | None = None
    slug: str | None = None
    display_name: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class ApiKeyCreateResponse(BaseModel):
    """POST /enterprise/tenants/{tenant_id}/api-keys (`sak485-g`)."""

    model_config = {"extra": "allow"}

    tenant_id: str | None = None
    key_id: str | None = None
    key_prefix: str | None = None
    api_key: str | None = None
    label: str | None = None
    api_scopes: list[str] | None = None
    message: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.post(
    "/iam/bootstrap",
    response_model=IamBootstrapResponse,
    response_model_exclude_none=True,
    summary="IAM bootstrap (`sak485-g`)",
    responses=enterprise_peel_json_openapi_responses(),  # sak496-e
)
def bootstrap_iam(
    _admin: AdminDep,
    _gate: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    iam.ensure_default_tenant()
    tenants = iam.list_tenants()
    ops = next((t for t in tenants if t.tenant_id != DEFAULT_TENANT_ID), None)
    if ops is None:
        ops = iam.create_tenant(slug="ops", display_name="Operations")
    key = iam.create_api_key(
        tenant_id=ops.tenant_id,
        label="bootstrap",
        role_taxonomy_keys=["planner", "backend_writer"],
        api_scopes=list(DEFAULT_ADMIN_SCOPES),
    )
    if hasattr(iam, "log_iam_action"):
        iam.log_iam_action(
            action="iam.bootstrap",
            tenant_id=ops.tenant_id,
            actor_key_id=key.key_id,
            detail={"tenant_slug": ops.slug},
        )
    return {
        "tenant_id": str(ops.tenant_id),
        "tenant_slug": ops.slug,
        "key_id": str(key.key_id),
        "key_prefix": key.key_prefix,
        "api_key": key.api_key,
        "role_taxonomy_keys": ["backend_writer", "planner"],
        "api_scopes": sorted(DEFAULT_ADMIN_SCOPES),
        "message": "Store api_key securely; it is shown once.",
    }


@router.get(
    "/iam/me",
    response_model=IamMeResponse,
    response_model_exclude_none=True,
    summary="IAM me (`sak485-g`)",
    responses=enterprise_peel_json_openapi_responses(),  # sak496-e
)
def iam_me(_gate: EnterpriseDep) -> dict[str, Any]:
    ctx = get_auth_context()
    if ctx is None:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "missing authenticated IAM context"),
        )
    return {
        "tenant_id": str(ctx.tenant_id),
        "tenant_slug": ctx.tenant_slug,
        "key_id": str(ctx.key_id),
        "role_taxonomy_keys": list(ctx.role_taxonomy_keys),
        "api_scopes": list(ctx.api_scopes),
    }


@router.get(
    "/tenants",
    response_model=TenantsListResponse,
    response_model_exclude_none=True,
    summary="List tenants (`sak485-g`)",
    responses=enterprise_peel_json_openapi_responses(),  # sak496-e
)
def list_tenants(_gate: EnterpriseDep, iam: IamStoreDep) -> dict[str, Any]:
    rows = iam.list_tenants()
    return {
        "tenants": [
            {
                "tenant_id": str(t.tenant_id),
                "slug": t.slug,
                "display_name": t.display_name,
            }
            for t in rows
        ],
    }


@router.post(
    "/tenants",
    response_model=TenantCreateResponse,
    response_model_exclude_none=True,
    summary="Create tenant (`sak485-g`)",
    responses=enterprise_peel_json_openapi_responses(),  # sak496-e
)
def create_tenant(
    body: TenantCreateBody,
    _gate: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    try:
        tenant = iam.create_tenant(slug=body.slug, display_name=body.display_name)
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=problem("tenant_conflict", str(exc)),
        ) from exc
    return {
        "tenant_id": str(tenant.tenant_id),
        "slug": tenant.slug,
        "display_name": tenant.display_name,
    }


@router.post(
    "/tenants/{tenant_id}/api-keys",
    response_model=ApiKeyCreateResponse,
    response_model_exclude_none=True,
    summary="Create API key (`sak485-g`)",
    responses=enterprise_peel_json_openapi_responses(),  # sak496-e
)
def create_api_key(
    tenant_id: UUID,
    body: ApiKeyCreateBody,
    _gate: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    if iam.get_tenant(tenant_id) is None:
        raise HTTPException(
            status_code=404,
            detail=problem("tenant_not_found", f"unknown tenant_id: {tenant_id}"),
        )
    key = iam.create_api_key(
        tenant_id=tenant_id,
        label=body.label,
        role_taxonomy_keys=body.role_taxonomy_keys,
        api_scopes=body.api_scopes or list(DEFAULT_USER_SCOPES),
    )
    return {
        "tenant_id": str(key.tenant_id),
        "key_id": str(key.key_id),
        "key_prefix": key.key_prefix,
        "api_key": key.api_key,
        "label": key.label,
        "api_scopes": list(normalize_scopes(body.api_scopes)),
        "message": "Store api_key securely; it is shown once.",
    }
