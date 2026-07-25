from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import OrchDep, StoreDep
from api.errors import problem
from api.schemas.peel_responses import long_tail_json_openapi_responses, with_long_tail_peel_503
from standards import (
    mart_catalog,
    run_bundle,
    run_bundles_for_facade,
    run_profile,
    run_stream,
)
from standards.persist import persist_run_standards, standards_profile_from_rows
from standards.preset_defaults import preset_defaults_summary
from standards.profile import (
    StandardsProfile,
    resolve_standards_profile,
    standards_platform_enabled,
)
from standards.registry import load_facade_manifest
from standards.user_profiles import (
    load_user_standards_profiles,
    upsert_user_standards_profile,
)
from standards.verdict import VerdictMode
from standards.workspace_standards import run_workspace_standards

router = APIRouter()


def _run_workspace_from_store(run_id: UUID, store: StoreDep):
    from pathlib import Path

    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    meta = rows[0].get("metadata") if rows else {}
    if not isinstance(meta, dict):
        meta = {}
    project = meta.get("project") if isinstance(meta.get("project"), dict) else {}
    workspace_raw = project.get("workspace_path") or project.get("workspace")
    if not isinstance(workspace_raw, str) or not workspace_raw.strip():
        raise HTTPException(
            status_code=409,
            detail=problem("workspace_missing", "run has no attached workspace path"),
        )
    return rows, Path(workspace_raw)


class StandardsRunBody(BaseModel):
    stream: str | None = None
    bundle: str | None = None
    profile: str | None = None


class StandardsProfileBody(BaseModel):
    facade_id: str | None = None
    bundles: list[str] = Field(default_factory=list)
    connectors: list[str] = Field(default_factory=list)
    verdict_overrides: dict[str, VerdictMode] = Field(default_factory=dict)


class UserStandardsProfileBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    facade_id: str | None = None
    bundles: list[str] = Field(default_factory=list)
    connectors: list[str] = Field(default_factory=list)


class StandardsRegistryResponse(BaseModel):
    """GET /standards/registry (`sak483-e`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


class StandardsPresetResponse(BaseModel):
    """GET /standards/presets/{preset_id} (`sak483-e`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


class StandardsPresetDefaultsResponse(BaseModel):
    """GET /standards/presets/{preset_id}/defaults (`sak483-e`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


class RunStandardsResponse(BaseModel):
    """GET/PUT /runs/{run_id}/standards (`sak483-e`)."""

    model_config = {"extra": "allow"}

    run_id: str | None = None
    standards_effective: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class RunStandardsReportResponse(BaseModel):
    """GET /runs/{run_id}/standards/report (`sak483-e`)."""

    model_config = {"extra": "allow"}

    run_id: str | None = None
    passed: bool | None = None
    failing_check_ids: list[str] | None = None
    results: list[dict[str, Any]] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class RunStandardsRunResponse(BaseModel):
    """POST /runs/{run_id}/standards/run (`sak483-e`)."""

    model_config = {"extra": "allow"}

    run_id: str | None = None
    result: dict[str, Any] | None = None
    results: list[dict[str, Any]] | dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class UserStandardsProfilesResponse(BaseModel):
    """GET /users/me/standards-profile (`sak483-e`)."""

    model_config = {"extra": "allow"}

    profiles: list[dict[str, Any]] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class UserStandardsProfileResponse(BaseModel):
    """PUT /users/me/standards-profile/{profile_id} (`sak483-e`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/standards/registry",
    response_model=StandardsRegistryResponse,
    response_model_exclude_none=True,
    summary="Standards registry (`sak483-e`)",
    responses=long_tail_json_openapi_responses(),  # sak500-e
)
def get_standards_registry() -> dict[str, Any]:
    if not standards_platform_enabled():
        raise HTTPException(
            status_code=503,
            detail=problem("standards_disabled", "standards platform is disabled"),
        )
    return mart_catalog()


@router.get(
    "/standards/presets/{preset_id}",
    response_model=StandardsPresetResponse,
    response_model_exclude_none=True,
    summary="Standards preset (`sak483-e`)",
    responses=with_long_tail_peel_503(),  # sak506-h
)
def get_standards_preset(preset_id: str, level: int = 5) -> dict[str, Any]:
    manifest = load_facade_manifest(preset_id)
    if manifest is None:
        raise HTTPException(
            status_code=404,
            detail=problem("preset_not_found", f"standards preset not found: {preset_id}"),
        )
    return {
        **manifest,
        "defaults": preset_defaults_summary(preset_id, level),
    }


@router.get(
    "/standards/presets/{preset_id}/defaults",
    response_model=StandardsPresetDefaultsResponse,
    response_model_exclude_none=True,
    summary="Standards preset defaults (`sak483-e`)",
    responses=with_long_tail_peel_503(),  # sak506-h
)
def get_standards_preset_defaults(preset_id: str, level: int = 5) -> dict[str, Any]:
    manifest = load_facade_manifest(preset_id)
    if manifest is None:
        raise HTTPException(
            status_code=404,
            detail=problem("preset_not_found", f"standards preset not found: {preset_id}"),
        )
    return preset_defaults_summary(preset_id, level)


@router.get(
    "/runs/{run_id}/standards",
    response_model=RunStandardsResponse,
    response_model_exclude_none=True,
    summary="Run standards GET (`sak483-e`)",
    responses=with_long_tail_peel_503(),  # sak506-c
)
def get_run_standards(run_id: UUID, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    meta = rows[0].get("metadata") if rows else {}
    if not isinstance(meta, dict):
        meta = {}
    project = meta.get("project") if isinstance(meta.get("project"), dict) else {}
    workspace_raw = project.get("workspace_path") or project.get("workspace")
    workspace = None
    if isinstance(workspace_raw, str) and workspace_raw.strip():
        from pathlib import Path

        workspace = Path(workspace_raw)
    profile = standards_profile_from_rows(rows, workspace=workspace)
    return {"run_id": str(run_id), "standards_effective": profile.to_dict()}


@router.get(
    "/runs/{run_id}/standards/report",
    response_model=RunStandardsReportResponse,
    response_model_exclude_none=True,
    summary="Run standards report (`sak483-e`)",
    responses=with_long_tail_peel_503(),  # sak506-c
)
def get_run_standards_report(run_id: UUID, store: StoreDep) -> dict[str, Any]:
    _, workspace = _run_workspace_from_store(run_id, store)
    profile = resolve_standards_profile(workspace=workspace)
    passed, results = run_workspace_standards(workspace, profile=profile)
    failing = [
        c.check_id
        for result in results
        for c in result.checks
        if not c.passed and c.verdict in ("hard_gate", "critique")
    ]
    return {
        "run_id": str(run_id),
        "passed": passed,
        "failing_check_ids": failing,
        "results": [r.to_dict() for r in results],
    }


@router.put(
    "/runs/{run_id}/standards",
    response_model=RunStandardsResponse,
    response_model_exclude_none=True,
    summary="Run standards PUT (`sak483-e`)",
    responses=with_long_tail_peel_503(),  # sak506-i
)
def put_run_standards(run_id: UUID, body: StandardsProfileBody, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    meta = rows[0].get("metadata") if rows else {}
    if not isinstance(meta, dict):
        meta = {}
    project = meta.get("project") if isinstance(meta.get("project"), dict) else {}
    workspace_raw = project.get("workspace_path") or project.get("workspace")
    workspace = None
    if isinstance(workspace_raw, str) and workspace_raw.strip():
        from pathlib import Path

        workspace = Path(workspace_raw)
    effective = resolve_standards_profile(workspace=workspace, facade_id=body.facade_id)
    bundle_ids = list(body.bundles) if body.bundles else list(effective.bundle_ids)
    connector_ids = list(body.connectors) if body.connectors else list(effective.connector_ids)
    overrides = body.verdict_overrides if body.verdict_overrides else effective.verdict_overrides
    merged = StandardsProfile(
        profile_id=effective.profile_id,
        facade_id=body.facade_id or effective.facade_id,
        bundle_ids=tuple(bundle_ids),
        connector_ids=tuple(connector_ids),
        stream_ids=effective.stream_ids,
        verdict_overrides=overrides,
        custom=True,
    )
    persist_run_standards(store, run_id, merged, workspace=workspace)
    return {"run_id": str(run_id), "standards_effective": merged.to_dict()}


@router.post(
    "/runs/{run_id}/standards/run",
    response_model=RunStandardsRunResponse,
    response_model_exclude_none=True,
    summary="Run standards execution (`sak483-e`)",
    responses=with_long_tail_peel_503(),  # sak506-i
)
def post_run_standards_run(run_id: UUID, body: StandardsRunBody, store: StoreDep) -> dict[str, Any]:
    _, workspace = _run_workspace_from_store(run_id, store)
    if body.stream:
        result = run_stream(body.stream, workspace=workspace)
        return {"run_id": str(run_id), "result": result.to_dict()}
    if body.bundle:
        result = run_bundle(body.bundle, workspace=workspace)
        return {"run_id": str(run_id), "result": result.to_dict()}
    if body.profile:
        results = run_profile(body.profile, workspace=workspace)
        return {
            "run_id": str(run_id),
            "results": {k: v.to_dict() for k, v in results.items()},
        }
    profile = resolve_standards_profile(workspace=workspace)
    bundle_results = run_bundles_for_facade(profile.facade_id or "", workspace=workspace)
    return {
        "run_id": str(run_id),
        "results": [r.to_dict() for r in bundle_results],
    }


@router.get(
    "/users/me/standards-profile",
    response_model=UserStandardsProfilesResponse,
    response_model_exclude_none=True,
    summary="User standards profiles GET (`sak483-e`)",
    responses=with_long_tail_peel_503(),  # sak507-c
)
def get_user_standards_profile(orch: OrchDep) -> dict[str, Any]:
    profiles = load_user_standards_profiles(orch.repo_root)
    return {"profiles": [p.to_dict() for p in profiles.values()]}


@router.put(
    "/users/me/standards-profile/{profile_id}",
    response_model=UserStandardsProfileResponse,
    response_model_exclude_none=True,
    summary="User standards profile PUT (`sak483-e`)",
    responses=with_long_tail_peel_503(),  # sak507-c
)
def put_user_standards_profile(
    profile_id: str,
    body: UserStandardsProfileBody,
    orch: OrchDep,
) -> dict[str, Any]:
    pid = profile_id.strip()
    if not pid:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_profile_id", "profile_id is required"),
        )
    entry = upsert_user_standards_profile(
        profile_id=pid,
        name=body.name,
        facade_id=body.facade_id,
        bundle_ids=body.bundles,
        connector_ids=body.connectors,
        repo_root=orch.repo_root,
    )
    return entry.to_dict()
