from __future__ import annotations

from typing import Any

from agent_core.models.backlog import DeliveryBacklog, SliceStatus
from nimbusware_maker.stack_manifest import manifest_from_requirements


def validate_manifest_backlog(
    backlog: DeliveryBacklog,
    requirements: dict[str, Any] | None,
) -> list[str]:
    manifest = manifest_from_requirements(requirements)
    if manifest is None or not manifest.surfaces:
        return []
    errors: list[str] = []
    seen_surfaces: set[str] = set()
    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                sid = str(sl.surface_id or "").strip()
                if sid:
                    seen_surfaces.add(sid)
    for surface in manifest.surfaces:
        if surface == "contract":
            continue
        if surface not in seen_surfaces:
            errors.append(f"backlog missing slice for manifest surface {surface!r}")
    if manifest.scope_narrowed and "web" in manifest.surfaces:
        errors.append("scope_narrowed manifest must not include web surface")
    passed_api_only = manifest.surfaces == ("api",) or manifest.surfaces == ["api"]
    if passed_api_only and "web" in seen_surfaces:
        errors.append("api-only manifest but backlog includes web slices")
    return errors


def manifest_template_id(requirements: dict[str, Any] | None) -> str | None:
    manifest = manifest_from_requirements(requirements)
    if manifest is None:
        return None
    surfaces = list(manifest.surfaces)
    if "web" in surfaces and "api" in surfaces:
        return "fullstack_todo"
    if surfaces == ["api"] or surfaces == ("api",):
        return "todo_api"
    return None
