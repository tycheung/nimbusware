from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.routing import APIRouter as _APIRouter

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem

router: _APIRouter = APIRouter()


@router.get("/runs/{run_id}/timeline/{section}/explain")
def get_timeline_section_explain(
    run_id: UUID,
    section: str,
    store: StoreDep,
) -> dict:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    return {
        "run_id": str(run_id),
        "section": section,
        "markdown": f"Timeline section **{section}** ({len(rows)} events). "
        "Detailed explainers remain in Python display modules; expand this BFF as needed.",
        "event_count": len(rows),
    }
