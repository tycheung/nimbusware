"""Enterprise IAM routes (Lane D / fo201)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import IamStoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.enterprise import EnterpriseDep
from nimbusware_iam.constants import DEFAULT_TENANT_ID
from nimbusware_iam.context import get_auth_context

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class TenantCreateBody(BaseModel):
    slug: str = Field(min_length=1, max_length=64)
    display_name: str = Field(default="", max_length=256)


class ApiKeyCreateBody(BaseModel):
    label: str = Field(default="", max_length=128)
    role_taxonomy_keys: list[str] = Field(default_factory=list)


@router.post("/iam/bootstrap")
def bootstrap_iam(
    _admin: AdminDep,
    _gate: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    """Admin-only first tenant + API key for Enterprise installs."""
    iam.ensure_default_tenant()
    tenants = iam.list_tenants()
    ops = next((t for t in tenants if t.tenant_id != DEFAULT_TENANT_ID), None)
    if ops is None:
        ops = iam.create_tenant(slug="ops", display_name="Operations")
    key = iam.create_api_key(
        tenant_id=ops.tenant_id,
        label="bootstrap",
        role_taxonomy_keys=["planner", "backend_writer"],
    )
    return {
        "tenant_id": str(ops.tenant_id),
        "tenant_slug": ops.slug,
        "key_id": str(key.key_id),
        "key_prefix": key.key_prefix,
        "api_key": key.api_key,
        "role_taxonomy_keys": ["backend_writer", "planner"],
        "message": "Store api_key securely; it is shown once.",
    }


@router.get("/iam/me")
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
    }


@router.get("/tenants")
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


@router.post("/tenants")
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


@router.post("/tenants/{tenant_id}/api-keys")
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
    )
    return {
        "tenant_id": str(key.tenant_id),
        "key_id": str(key.key_id),
        "key_prefix": key.key_prefix,
        "api_key": key.api_key,
        "label": key.label,
        "message": "Store api_key securely; it is shown once.",
    }
