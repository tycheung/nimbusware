from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

from api.deps import StoreDep
from api.errors import problem
from api.export_peel import early_export_json_miss
from api.schemas.openapi import PROBLEM_RESPONSE_404
from api.schemas.peel_responses import ExportErrorResponse, with_long_tail_peel_503
from maker.workspace.workspace import resolve_run_workspace
from orchestrator.factory.evidence import (
    build_factory_evidence_bundle,
    export_factory_evidence_zip,
)
from orchestrator.factory.evidence_html import render_factory_evidence_html

router = APIRouter()


class FactoryEvidenceResponse(BaseModel):
    """GET /runs/{run_id}/factory-evidence (`sak486-g`)."""

    model_config = {"extra": "allow"}

    run_id: str | None = None
    factory_complete: bool | None = None
    factory_status: dict[str, Any] | None = None
    put_e2e: dict[str, Any] | None = None
    factory_stages: list[dict[str, Any]] | None = None
    put_artifacts: dict[str, Any] | None = None
    evidence: dict[str, Any] | None = None
    scorecard_rows: list[dict[str, str]] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class FactoryEvidenceScorecardExportResponse(ExportErrorResponse):
    """GET /runs/{run_id}/factory-evidence/scorecard.html peel miss (`sak488-e`)."""

    pass


class FactoryEvidenceZipExportResponse(ExportErrorResponse):
    """GET /runs/{run_id}/factory-evidence/export peel miss (`sak488-e`)."""

    pass


@router.get(
    "/runs/{run_id}/factory-evidence",
    response_model=FactoryEvidenceResponse,
    response_model_exclude_none=True,
    responses=with_long_tail_peel_503({404: PROBLEM_RESPONSE_404}),  # sak502-i
)
def get_factory_evidence(run_id: UUID, store: StoreDep) -> FactoryEvidenceResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    workspace = resolve_run_workspace(rows)
    body = build_factory_evidence_bundle(rows, workspace=workspace)
    body["run_id"] = str(run_id)
    return FactoryEvidenceResponse.model_validate(body)


@router.get(
    "/runs/{run_id}/factory-evidence/scorecard.html",
    response_class=HTMLResponse,
    response_model=None,
    responses=with_long_tail_peel_503(
        {
            200: {
                "content": {
                    "text/html": {},
                    "application/json": {"model": FactoryEvidenceScorecardExportResponse},
                },
            },
            404: PROBLEM_RESPONSE_404,
        },
    ),  # sak511-g
)
def factory_evidence_scorecard_html(run_id: UUID, store: StoreDep):
    if miss := early_export_json_miss(feature="factory_evidence_scorecard"):
        return miss
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    workspace = resolve_run_workspace(rows)
    bundle = build_factory_evidence_bundle(rows, workspace=workspace)
    bundle["run_id"] = str(run_id)
    return HTMLResponse(content=render_factory_evidence_html(bundle))


@router.get(
    "/runs/{run_id}/factory-evidence/export",
    response_model=None,
    responses=with_long_tail_peel_503(
        {
            200: {
                "content": {
                    "application/zip": {},
                    "application/json": {"model": FactoryEvidenceZipExportResponse},
                },
            },
            404: PROBLEM_RESPONSE_404,
        },
    ),  # sak511-g
)
def export_factory_evidence(run_id: UUID, store: StoreDep):
    if miss := early_export_json_miss(feature="factory_evidence_export"):
        return miss
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    workspace = resolve_run_workspace(rows)
    payload = export_factory_evidence_zip(rows, workspace=workspace, run_id=str(run_id))
    filename = f"factory-evidence-{run_id}.zip"
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
