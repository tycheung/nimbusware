from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_maker.workspace import (
    project_id_from_run_created_metadata,
    run_created_metadata_from_rows,
)
from nimbusware_orchestrator.context_artifacts import (
    get_context_artifact,
    insert_context_artifact_into_run,
)

router = APIRouter()


@router.post(
    "/runs/{run_id}/context-artifacts/{artifact_id}/insert",
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def post_insert_context_artifact(
    run_id: UUID,
    artifact_id: str,
    store: StoreDep,
) -> dict[str, str]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    meta = run_created_metadata_from_rows(rows)
    project_id = project_id_from_run_created_metadata(meta)
    if project_id is None:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "run has no project_id; cannot resolve artifacts"),
        )
    artifact = get_context_artifact(project_id, artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "artifact_not_found",
                "context artifact not found",
                details={"artifact_id": artifact_id.strip()},
            ),
        )
    result = insert_context_artifact_into_run(
        store,
        run_id=run_id,
        artifact=artifact,
    )
    return {"run_id": str(run_id), **{k: str(v) for k, v in result.items()}}
