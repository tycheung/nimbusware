from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from nimbusware_maker.deploy_target_enforcement import (
    DEFAULT_DEPLOY_ENVIRONMENT,
    normalize_deploy_environment,
)


class StackManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surfaces: tuple[str, ...] = ()
    stacks: dict[str, str] = Field(default_factory=dict)
    hosting: str = "local"
    recommended: bool = False
    scope_narrowed: bool = False
    frozen_at: str | None = None
    confirmed: bool = False
    discovery_summary: dict[str, str] = Field(default_factory=dict)
    deploy_environment: str = DEFAULT_DEPLOY_ENVIRONMENT

    @field_validator("deploy_environment")
    @classmethod
    def _validate_deploy_environment(cls, value: str) -> str:
        return normalize_deploy_environment(value)


def manifest_from_requirements(requirements: dict[str, Any] | None) -> StackManifest | None:
    if not isinstance(requirements, dict):
        return None
    raw = requirements.get("stack_manifest")
    if not isinstance(raw, dict):
        return None
    return parse_stack_manifest(raw)


def parse_stack_manifest(raw: dict[str, Any]) -> StackManifest:
    surfaces_raw = raw.get("surfaces")
    surfaces: tuple[str, ...]
    if isinstance(surfaces_raw, list):
        surfaces = tuple(str(s) for s in surfaces_raw if str(s).strip())
    else:
        surfaces = ()
    stacks_raw = raw.get("stacks")
    stacks = {str(k): str(v) for k, v in stacks_raw.items()} if isinstance(stacks_raw, dict) else {}
    summary_raw = raw.get("discovery_summary")
    summary = (
        {str(k): str(v) for k, v in summary_raw.items()} if isinstance(summary_raw, dict) else {}
    )
    return StackManifest(
        surfaces=surfaces,
        stacks=stacks,
        hosting=str(raw.get("hosting") or "local").strip() or "local",
        recommended=bool(raw.get("recommended")),
        scope_narrowed=bool(raw.get("scope_narrowed")),
        frozen_at=str(raw.get("frozen_at") or "").strip() or None,
        confirmed=bool(raw.get("confirmed")),
        discovery_summary=summary,
        deploy_environment=normalize_deploy_environment(
            str(raw.get("deploy_environment") or DEFAULT_DEPLOY_ENVIRONMENT)
        ),
    )


def discovery_summary_from_answers(answers: dict[str, str] | None) -> dict[str, str]:
    if not isinstance(answers, dict):
        return {}
    out: dict[str, str] = {}
    for key in ("client_form", "backend_stack", "frontend_stack", "hosting", "stack_defer"):
        val = str(answers.get(key) or "").strip()
        if val:
            out[key] = val
    return out


def freeze_manifest(
    raw: dict[str, Any],
    *,
    answers: dict[str, str] | None = None,
    confirmed: bool = False,
) -> StackManifest:
    manifest = parse_stack_manifest(raw)
    summary = discovery_summary_from_answers(answers) or dict(manifest.discovery_summary)
    return manifest.model_copy(
        update={
            "frozen_at": datetime.now(timezone.utc).isoformat(),
            "confirmed": confirmed or manifest.confirmed,
            "discovery_summary": summary,
        },
    )


def validate_frozen_manifest(
    manifest: StackManifest,
    *,
    repo_root: Any | None = None,
    tenant_slug: str | None = None,
) -> list[str]:
    from nimbusware_orchestrator.fleet_stack_policy import tenant_stack_policy

    errors: list[str] = []
    if not manifest.surfaces:
        errors.append("manifest has no surfaces")
    stack_policy = tenant_stack_policy(tenant_slug, repo_root=repo_root)
    if stack_policy.restricts_stacks():
        for surface in manifest.surfaces:
            allowed = stack_policy.allowed_stacks.get(surface)
            if allowed is None:
                errors.append(f"surface {surface!r} not allowed by tenant stack policy")
                continue
            chosen = manifest.stacks.get(surface)
            if chosen and chosen != allowed:
                errors.append(
                    f"stack {chosen!r} for surface {surface!r} "
                    f"not allowed (tenant requires {allowed!r})",
                )
    from nimbusware_orchestrator.stack_catalog import load_stack_catalog, resolve_manifest_stacks

    catalog = load_stack_catalog(repo_root)
    for surface in manifest.surfaces:
        stack_id = manifest.stacks.get(surface)
        if not stack_id:
            errors.append(f"surface {surface!r} missing stack_id")
            continue
        if stack_id not in catalog:
            errors.append(f"unknown stack_id {stack_id!r} for surface {surface!r}")
            continue
        if catalog[stack_id].surface != surface:
            errors.append(
                f"stack {stack_id!r} surface {catalog[stack_id].surface!r} "
                f"does not match manifest surface {surface!r}",
            )
    resolved = resolve_manifest_stacks(manifest.model_dump(), repo_root=repo_root)
    for surface in manifest.surfaces:
        if surface not in resolved:
            errors.append(f"surface {surface!r} could not be resolved in catalog")
    return errors
