from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from agent_core.models import EventType
from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.read_models.maker_progress import maker_progress_from_events

router = APIRouter()

_TERMINAL = frozenset(
    {
        EventType.RUN_COMPLETED.value,
        EventType.RUN_FAILED.value,
        EventType.RUN_ESCALATED.value,
    },
)


def _sse_pack(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.get("/runs/{run_id}/maker-progress/stream")
def get_maker_progress_stream(
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
        idle_rounds = 0
        while idle_rounds < 30:
            current = store.list_run_events(str(run_id))
            new_rows = [r for r in current if int(r.get("store_seq") or 0) > last_seq]
            if new_rows:
                idle_rounds = 0
                for row in new_rows:
                    last_seq = max(last_seq, int(row.get("store_seq") or 0))
                    yield _sse_pack(
                        "event",
                        {
                            "store_seq": last_seq,
                            "event_type": row.get("event_type"),
                        },
                    )
                body = maker_progress_from_events(current)
                body["run_id"] = str(run_id)
                yield _sse_pack("progress", body)
                if any(str(r.get("event_type")) in _TERMINAL for r in new_rows):
                    yield _sse_pack("done", {"run_id": str(run_id)})
                    return
            else:
                idle_rounds += 1
                yield _sse_pack("heartbeat", {"cursor": last_seq})
            await asyncio.sleep(poll_seconds)
        yield _sse_pack("done", {"run_id": str(run_id), "reason": "idle_timeout"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
