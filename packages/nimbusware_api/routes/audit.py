from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response

from agent_core.models import serialize_event_persistent, validate_event_dict
from hermes_orchestrator.audit_export import build_audit_bundle_bytes
from hermes_orchestrator.policy_snapshot_diff import policy_snapshot_from_run_created_metadata
from hermes_store.protocol import serialized_event_from_row
from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import (
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
)
from nimbusware_maker.workspace import run_created_metadata_from_rows

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
    payload = build_audit_bundle_bytes(run_id=rid, events=events, policy_snapshot=snap)
    return Response(
        content=payload,
        media_type="application/gzip",
        headers={"Content-Disposition": f'attachment; filename="hermes-audit-{rid}.tar.gz"'},
    )
