from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from nimbusware_api.deps import OrchDep
from nimbusware_api.errors import problem
from nimbusware_api.user import UserDep, maker_user_id_str
from nimbusware_config.provider_connections import (
    ProviderConnectionStore,
    _row_to_public,
    encode_secret_payload,
)
from nimbusware_env.edition import is_enterprise
from nimbusware_env.env_flags import nimbusware_collab_enabled, nimbusware_database_url
from nimbusware_iam.context import get_auth_context, resolve_store_tenant_id
from nimbusware_orchestrator.provider_registry import (
    load_provider_presets,
    load_subscription_provider_presets,
    probe_connection_row,
    subscription_preset_by_id,
)

router = APIRouter(tags=["platform"])


class ProviderConnectionBody(BaseModel):
    connection_id: UUID | None = None
    provider_id: str = Field(min_length=1, max_length=80)
    label: str = Field(default="", max_length=200)
    connection_kind: Literal["api_key", "subscription"] = "api_key"
    base_url: str | None = Field(default=None, max_length=500)
    default_model_id: str | None = Field(default=None, max_length=200)
    api_key: str | None = Field(default=None, max_length=500)
    subscription_connected: bool = False


def _connection_user_id(request: Request) -> str:
    if is_enterprise():
        ctx = get_auth_context()
        if ctx is None:
            return ""
        return str(ctx.key_id)
    if nimbusware_collab_enabled():
        return maker_user_id_str(request)
    return ""


def _connection_tenant_id() -> str | None:
    return str(resolve_store_tenant_id())


def _store() -> ProviderConnectionStore:
    url = nimbusware_database_url()
    if not url:
        raise HTTPException(
            status_code=503,
            detail=problem("service_unavailable", "NIMBUSWARE_DATABASE_URL is not configured"),
        )
    return ProviderConnectionStore(url)


@router.get("/platform/provider-presets")
def list_provider_presets(orch: OrchDep, _: UserDep) -> dict[str, Any]:
    return {
        "providers": load_provider_presets(orch.repo_root),
        "subscription_providers": load_subscription_provider_presets(orch.repo_root),
    }


class SubscriptionLinkBody(BaseModel):
    provider_id: str = Field(min_length=1, max_length=80)
    subscription_connected: bool = True
    default_model_id: str | None = Field(default=None, max_length=200)


@router.post("/platform/provider-connections/subscription-link")
def link_subscription_provider(
    body: SubscriptionLinkBody, request: Request, orch: OrchDep, _: UserDep
) -> dict[str, Any]:
    preset = subscription_preset_by_id(orch.repo_root, body.provider_id)
    if preset is None:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", f"unknown subscription provider: {body.provider_id}"),
        )
    store = _store()
    user_id = _connection_user_id(request)
    secret_blob = encode_secret_payload(
        connection_kind="subscription",
        subscription_connected=body.subscription_connected,
    )
    existing = [
        r
        for r in store.list_for_user(user_id=user_id, tenant_id=_connection_tenant_id())
        if r.provider_id == body.provider_id and r.connection_kind == "subscription"
    ]
    connection_id = existing[0].connection_id if existing else None
    row = store.upsert(
        connection_id=connection_id,
        user_id=user_id,
        tenant_id=_connection_tenant_id(),
        provider_id=body.provider_id,
        label=str(preset.get("label") or body.provider_id),
        connection_kind="subscription",
        base_url=None,
        default_model_id=body.default_model_id,
        secret_blob=secret_blob,
    )
    return {"connection": _row_to_public(row), "oauth_hint": preset.get("oauth_hint")}


@router.get("/platform/provider-connections")
def list_provider_connections(request: Request, _: UserDep) -> dict[str, Any]:
    store = _store()
    user_id = _connection_user_id(request)
    rows = store.list_for_user(user_id=user_id, tenant_id=_connection_tenant_id())
    return {"connections": [_row_to_public(r) for r in rows]}


@router.put("/platform/provider-connections")
def upsert_provider_connection(
    body: ProviderConnectionBody, request: Request, _: UserDep
) -> dict[str, Any]:
    store = _store()
    user_id = _connection_user_id(request)
    secret_blob = None
    if body.api_key is not None or body.connection_kind == "subscription":
        secret_blob = encode_secret_payload(
            connection_kind=body.connection_kind,
            api_key=body.api_key,
            subscription_connected=body.subscription_connected,
        )
    row = store.upsert(
        connection_id=body.connection_id,
        user_id=user_id,
        tenant_id=_connection_tenant_id(),
        provider_id=body.provider_id,
        label=body.label or body.provider_id,
        connection_kind=body.connection_kind,
        base_url=body.base_url,
        default_model_id=body.default_model_id,
        secret_blob=secret_blob,
    )
    return {"connection": _row_to_public(row)}


@router.delete("/platform/provider-connections/{connection_id}")
def delete_provider_connection(connection_id: UUID, request: Request, _: UserDep) -> dict[str, Any]:
    store = _store()
    user_id = _connection_user_id(request)
    if not store.delete(connection_id, user_id=user_id):
        raise HTTPException(
            status_code=404,
            detail=problem("not_found", "provider connection not found"),
        )
    return {"deleted": True, "connection_id": str(connection_id)}


@router.post("/platform/provider-connections/{connection_id}/probe")
def probe_provider_connection(
    connection_id: UUID,
    orch: OrchDep,
    request: Request,
    _: UserDep,
    timeout_seconds: Annotated[float, Query(ge=1.0, le=60.0)] = 10.0,
) -> dict[str, Any]:
    store = _store()
    user_id = _connection_user_id(request)
    row = store.get(connection_id, user_id=user_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=problem("not_found", "provider connection not found"),
        )
    secret = store.get_secret(connection_id, user_id=user_id)
    result = probe_connection_row(
        orch.repo_root,
        provider_id=row.provider_id,
        connection_kind=row.connection_kind,
        base_url=row.base_url,
        api_key=secret.api_key if secret else None,
        subscription_connected=bool(secret and secret.subscription_connected),
        timeout_seconds=timeout_seconds,
    )
    updated = store.record_probe(connection_id, user_id=user_id, ok=bool(result.get("ok")))
    return {
        "probe": result,
        "connection": _row_to_public(updated) if updated else None,
    }
