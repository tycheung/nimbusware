from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response

from agent_core.models import serialize_event_persistent, validate_event_dict
from api.deps import StoreDep
from api.errors import problem
from api.schemas.openapi import (
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
)
from maker.intent.requirements import requirements_from_run_created_metadata
from maker.workspace.workspace import run_created_metadata_from_rows
from orchestrator.policy_snapshot_diff import policy_snapshot_from_run_created_metadata
from orchestrator.replay.audit_export import (
    build_audit_bundle_bytes,
    scope_snapshot_from_requirements,
    surface_outcomes_from_events,
)
from projections.builders.run_theater import build_run_theater_messages
from projections.exporters.theater_transcript import format_theater_transcript_md
from store.protocol import serialized_event_from_row

router = APIRouter(tags=["audit"])


@router.get(
    "/runs/{run_id}/audit-export",
    responses={
        200: {"content": {"application/gzip": {}}},
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def audit_export(run_id: UUID, store: StoreDep) -> Response:
    rid = str(run_id)
    rows = store.list_run_events(rid)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": rid}),
        )
    events = []
    for r in rows:
        d = serialized_event_from_row(r)
        ev = validate_event_dict(d)
        events.append(serialize_event_persistent(ev))
    meta = run_created_metadata_from_rows(rows)
    snap = policy_snapshot_from_run_created_metadata(meta)
    requirements = requirements_from_run_created_metadata(meta)
    theater_md = format_theater_transcript_md(
        run_id=rid,
        messages=build_run_theater_messages(rows),
    )
    payload = build_audit_bundle_bytes(
        run_id=rid,
        events=events,
        policy_snapshot=snap,
        theater_transcript_md=theater_md,
        scope_snapshot=scope_snapshot_from_requirements(requirements),
        surface_outcomes=surface_outcomes_from_events(rows),
    )
    return Response(
        content=payload,
        media_type="application/gzip",
        headers={"Content-Disposition": f'attachment; filename="nimbusware-audit-{rid}.tar.gz"'},
    )
