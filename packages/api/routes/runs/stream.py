from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from agent_core.models import EventType
from api.deps import StoreDep
from api.errors import problem
from api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_503
from api.schemas.peel_responses import SseStreamErrorResponse
from api.sse_peel import early_sse_peel_miss, sse_pack, sse_stream_openapi_responses
from projections.builders.maker_progress import maker_progress_from_events

router = APIRouter()

_TERMINAL = frozenset(
    {
        EventType.RUN_COMPLETED.value,
        EventType.RUN_FAILED.value,
        EventType.RUN_ESCALATED.value,
    },
)


def _progress_delta(prev: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    delta: dict[str, Any] = {}
    for key, value in current.items():
        if prev.get(key) != value:
            delta[key] = value
    return delta


@router.get(
    "/runs/{run_id}/maker-progress/stream",
    responses={
        **sse_stream_openapi_responses(
            miss_model=SseStreamErrorResponse,
            not_found=PROBLEM_RESPONSE_404,
        ),
        503: PROBLEM_RESPONSE_503,  # sak511-h
    },
)
def get_maker_progress_stream(
    run_id: UUID,
    store: StoreDep,
    cursor: int = Query(default=0, ge=0),
    poll_seconds: float = Query(default=1.0, ge=0.25, le=5.0),
) -> StreamingResponse:
    cached_rows = store.list_run_events(str(run_id))
    if not cached_rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    if cursor > 0:
        cached_rows = [r for r in cached_rows if int(r.get("store_seq") or 0) > cursor]

    async def generate() -> Any:
        if peel := early_sse_peel_miss(feature="maker_progress_stream"):
            yield peel
            return
        nonlocal cached_rows
        last_seq = max((int(r.get("store_seq") or 0) for r in cached_rows), default=cursor)
        prev_progress: dict[str, Any] | None = None
        idle_rounds = 0
        initial = maker_progress_from_events(cached_rows)
        initial["run_id"] = str(run_id)
        yield sse_pack("progress", initial)
        prev_progress = initial
        while idle_rounds < 30:
            new_rows = store.list_run_events_since(str(run_id), last_seq)
            if new_rows:
                idle_rounds = 0
                cached_rows.extend(new_rows)
                for row in new_rows:
                    last_seq = max(last_seq, int(row.get("store_seq") or 0))
                    yield sse_pack(
                        "event",
                        {
                            "store_seq": last_seq,
                            "event_type": row.get("event_type"),
                        },
                    )
                body = maker_progress_from_events(cached_rows)
                body["run_id"] = str(run_id)
                if prev_progress is not None:
                    delta = _progress_delta(prev_progress, body)
                    if delta:
                        yield sse_pack("progress_delta", delta)
                    else:
                        yield sse_pack("progress", body)
                else:
                    yield sse_pack("progress", body)
                prev_progress = body
                if any(str(r.get("event_type")) in _TERMINAL for r in new_rows):
                    yield sse_pack("done", {"run_id": str(run_id)})
                    return
            else:
                idle_rounds += 1
                yield sse_pack("heartbeat", {"cursor": last_seq})
            await asyncio.sleep(poll_seconds)
        yield sse_pack("done", {"run_id": str(run_id), "reason": "idle_timeout"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
