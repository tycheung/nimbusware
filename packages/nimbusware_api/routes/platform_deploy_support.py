from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from nimbusware_api.errors import problem
from nimbusware_env.env_flags import env_str
from nimbusware_iam.context import get_auth_context
from nimbusware_maker.deploy_environments import resolve_deploy_environment
from nimbusware_maker.deploy_pipeline_events import manifest_from_events
from nimbusware_maker.deploy_target_enforcement import (
    validate_credential_scopes,
    validate_manifest_deploy_target,
)


def resolved_deploy_environment(
    *,
    explicit: str | None,
    creds: dict[str, Any],
    rows: list[dict[str, Any]],
) -> str:
    try:
        return resolve_deploy_environment(
            explicit=explicit,
            credentials=creds,
            manifest_raw=manifest_from_events(rows),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc


def deploy_policy_context() -> tuple[str | None, str]:
    ctx = get_auth_context()
    tenant_slug = ctx.tenant_slug if ctx is not None else None
    setup_bundle = env_str("NIMBUSWARE_SETUP_BUNDLE").strip() or "default"
    return tenant_slug, setup_bundle


def deploy_approval_chain_for_tenant(tenant_slug: str | None, setup_bundle: str) -> str:
    if setup_bundle != "enterprise":
        return "maker_only"
    from nimbusware_orchestrator.fleet_deploy_approval_policy import tenant_deploy_approval_policy

    return tenant_deploy_approval_policy(tenant_slug).deploy_approval_chain


def enforce_manifest_deploy_target(
    rows: list[dict[str, Any]],
    *,
    tenant_slug: str | None,
    setup_bundle: str,
) -> None:
    ok, detail = validate_manifest_deploy_target(
        manifest_from_events(rows),
        tenant_slug=tenant_slug,
        setup_bundle=setup_bundle,
    )
    if not ok:
        raise HTTPException(
            status_code=403,
            detail=problem("deploy_target_denied", detail or "deploy target not allowed"),
        )


def enforce_credential_scopes(
    creds: dict[str, Any],
    *,
    tenant_slug: str | None,
    setup_bundle: str,
) -> None:
    ok, detail = validate_credential_scopes(
        creds,
        tenant_slug=tenant_slug,
        setup_bundle=setup_bundle,
    )
    if not ok:
        raise HTTPException(
            status_code=403,
            detail=problem("deploy_credential_scope_denied", detail or "credential scope denied"),
        )
