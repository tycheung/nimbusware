from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
) -> list[str]:
    from nimbusware_orchestrator.stack_catalog import load_stack_catalog, resolve_manifest_stacks

    errors: list[str] = []
    if not manifest.surfaces:
        errors.append("manifest has no surfaces")
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
