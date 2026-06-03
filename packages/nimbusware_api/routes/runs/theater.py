from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.read_models.run_theater import build_run_theater_messages
from nimbusware_api.routes.runs.stream import _sse_pack
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_projections.exporters.theater_transcript import format_theater_transcript_md

router = APIRouter()


class TheaterResponse(BaseModel):
    run_id: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0
    next_cursor: int | None = None


@router.get(
    "/runs/{run_id}/theater",
    response_model=TheaterResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_run_theater(
    run_id: UUID,
    store: StoreDep,
    cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> TheaterResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    all_msgs = build_run_theater_messages(rows)
    page = [m for m in all_msgs if int(m.get("store_seq") or 0) > cursor][:limit]
    next_c = int(page[-1]["store_seq"]) if page else None
    return TheaterResponse(
        run_id=str(run_id),
        messages=page,
        count=len(page),
        next_cursor=next_c,
    )


@router.get(
    "/runs/{run_id}/theater/export",
    responses={
        200: {"content": {"text/markdown": {}}},
        404: PROBLEM_RESPONSE_404,
    },
)
def export_run_theater(run_id: UUID, store: StoreDep) -> Response:
    rid = str(run_id)
    rows = store.list_run_events(rid)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": rid}),
        )
    messages = build_run_theater_messages(rows)
    md = format_theater_transcript_md(run_id=rid, messages=messages)
    return Response(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="hermes-theater-{rid}.md"'},
    )


@router.get("/runs/{run_id}/theater/stream")
def get_theater_stream(
    run_id: UUID,
    store: StoreDep,
    cursor: int = Query(default=0, ge=0),
    poll_seconds: float = Query(default=1.0, ge=0.25, le=5.0),
) -> StreamingResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )

    async def generate() -> Any:
        last_seq = cursor
        idle = 0
        while idle < 20:
            current = store.list_run_events(str(run_id))
            msgs = build_run_theater_messages(current)
            new_msgs = [m for m in msgs if int(m.get("store_seq") or 0) > last_seq]
            if new_msgs:
                idle = 0
                for m in new_msgs:
                    last_seq = max(last_seq, int(m.get("store_seq") or 0))
                    yield _sse_pack("theater", m)
            else:
                idle += 1
                yield _sse_pack("heartbeat", {"cursor": last_seq})
            await asyncio.sleep(poll_seconds)
        yield _sse_pack("done", {"run_id": str(run_id)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
