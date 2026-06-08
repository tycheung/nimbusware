from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_maker.workspace import resolve_run_workspace
from nimbusware_orchestrator.factory_evidence import (
    build_factory_evidence_bundle,
    export_factory_evidence_zip,
)

router = APIRouter()


class FactoryEvidenceResponse(BaseModel):
    run_id: str
    factory_complete: bool = False
    factory_status: dict | None = None
    put_e2e: dict | None = None
    factory_stages: list[dict] = Field(default_factory=list)
    put_artifacts: dict = Field(default_factory=dict)
    evidence: dict = Field(default_factory=dict)


@router.get(
    "/runs/{run_id}/factory-evidence",
    response_model=FactoryEvidenceResponse,
    responses={404: PROBLEM_RESPONSE_404},
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
    "/runs/{run_id}/factory-evidence/export",
    responses={404: PROBLEM_RESPONSE_404},
)
def export_factory_evidence(run_id: UUID, store: StoreDep) -> Response:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    workspace = resolve_run_workspace(rows)
    payload = export_factory_evidence_zip(rows, workspace=workspace)
    filename = f"factory-evidence-{run_id}.zip"
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
