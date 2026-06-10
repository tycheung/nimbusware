from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from agent_core.models import serialize_event_persistent, validate_event_dict
from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import (
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
)
from nimbusware_maker.workspace import resolve_run_workspace
from nimbusware_orchestrator.slice_diff_api import build_slice_diff_response
from nimbusware_store.protocol import serialized_event_from_row

router = APIRouter()


class SliceDiffStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loc_added: int
    loc_removed: int
    source: str
    file_count: int


class SliceDiffResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    slice_index: int = Field(ge=1)
    slice_id: str
    files: list[str]
    unified_diff: str
    stats: SliceDiffStats
    target_paths: list[str]


@router.get(
    "/runs/{run_id}/slices/{slice_index}/diff",
    response_model=SliceDiffResponse,
    responses={
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def get_slice_diff(run_id: UUID, slice_index: int, store: StoreDep) -> SliceDiffResponse:
    rid_s = str(run_id)
    rows = store.list_run_events(rid_s)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": rid_s}),
        )
    events: list[dict[str, Any]] = []
    for r in rows:
        d = serialized_event_from_row(r)
        ev = validate_event_dict(d)
        events.append(serialize_event_persistent(ev))
    ws = resolve_run_workspace(rows)
    body = build_slice_diff_response(ws, events, slice_index)
    if body is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "slice_not_found",
                "slice index not found for this run",
                details={"run_id": rid_s, "slice_index": slice_index},
            ),
        )
    stats = body["stats"]
    return SliceDiffResponse(
        run_id=rid_s,
        slice_index=body["slice_index"],
        slice_id=body["slice_id"],
        files=body["files"],
        unified_diff=body["unified_diff"],
        stats=SliceDiffStats(
            loc_added=int(stats["loc_added"]),
            loc_removed=int(stats["loc_removed"]),
            source=str(stats["source"]),
            file_count=int(stats["file_count"]),
        ),
        target_paths=body["target_paths"],
    )
