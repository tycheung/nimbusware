from __future__ import annotations

from typing import Any

DEPLOY_STACK_TO_TARGET: dict[str, str] = {
    "terraform_aws_ecs": "aws-ecs",
    "terraform_aws_static": "aws-static-site",
    "terraform_aws_static_site": "aws-static-site",
    "github_actions": "github-actions",
}


def deploy_target_from_manifest(manifest: dict[str, Any] | None) -> str | None:
    if not isinstance(manifest, dict):
        return None
    stacks = manifest.get("stacks")
    if not isinstance(stacks, dict):
        return None
    deploy_stack = str(stacks.get("deploy") or "").strip()
    if not deploy_stack:
        return None
    return DEPLOY_STACK_TO_TARGET.get(deploy_stack, deploy_stack)


def deploy_target_from_credentials(creds: dict[str, Any]) -> str | None:
    if creds.get("github_repo"):
        return "github-actions"
    if creds.get("aws_profile"):
        return "aws-ecs"
    return None


def allowed_deploy_targets_for_tenant(
    tenant_slug: str | None,
    *,
    setup_bundle: str | None = None,
    repo_root: Any | None = None,
) -> list[str]:
    bundle = (setup_bundle or "").strip().lower()
    if bundle and bundle != "enterprise":
        return []
    from nimbusware_orchestrator.fleet_deploy_policy import tenant_deploy_policy

    policy = tenant_deploy_policy(tenant_slug, repo_root=repo_root)
    return list(policy.allowed_deploy_targets)


def validate_deploy_target_allowed(
    target: str | None,
    *,
    tenant_slug: str | None = None,
    setup_bundle: str | None = None,
    repo_root: Any | None = None,
) -> tuple[bool, str | None]:
    if not target:
        return True, None
    allowed = allowed_deploy_targets_for_tenant(
        tenant_slug,
        setup_bundle=setup_bundle,
        repo_root=repo_root,
    )
    if not allowed:
        return True, None
    if target in allowed:
        return True, None
    return False, (
        f"Deploy target {target!r} is not in tenant allowlist "
        f"({', '.join(allowed) or 'none configured'})"
    )


def validate_manifest_deploy_target(
    manifest: dict[str, Any] | None,
    *,
    tenant_slug: str | None = None,
    setup_bundle: str | None = None,
    repo_root: Any | None = None,
) -> tuple[bool, str | None]:
    target = deploy_target_from_manifest(manifest)
    return validate_deploy_target_allowed(
        target,
        tenant_slug=tenant_slug,
        setup_bundle=setup_bundle,
        repo_root=repo_root,
    )


def validate_credential_scopes(
    creds: dict[str, Any],
    *,
    tenant_slug: str | None = None,
    setup_bundle: str | None = None,
    repo_root: Any | None = None,
) -> tuple[bool, str | None]:
    target = deploy_target_from_credentials(creds)
    return validate_deploy_target_allowed(
        target,
        tenant_slug=tenant_slug,
        setup_bundle=setup_bundle,
        repo_root=repo_root,
    )


def credential_scope_labels(creds: dict[str, Any]) -> list[str]:
    scopes: list[str] = []
    if creds.get("aws_profile"):
        scopes.append("aws")
    if creds.get("github_repo"):
        scopes.append("github")
    return scopes


def default_enterprise_deploy_policy() -> Any:
    from nimbusware_orchestrator.fleet_deploy_policy import (
        DEFAULT_ENTERPRISE_DEPLOY_TARGETS,
        FleetDeployPolicy,
    )

    return FleetDeployPolicy(
        tenant_slug="default",
        allowed_deploy_targets=DEFAULT_ENTERPRISE_DEPLOY_TARGETS,
    )
