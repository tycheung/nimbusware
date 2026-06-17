from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from nimbusware_api.deps import ChatStoreDep, CollabStoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import OptionalUserDep
from nimbusware_api.routes.chat_handlers import session_or_404 as _session_or_404
from nimbusware_api.routes.chat_collab_common import actor_user_id, require_collab_enabled
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_auth.permissions import require_session_participant
from nimbusware_env.env_flags import nimbusware_collab_enabled

router = APIRouter(prefix="/chat", tags=["maker"])


def _sse_pack(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.get(
    "/sessions/{session_id}/stream",
    responses={404: PROBLEM_RESPONSE_404},
)
def chat_session_stream(
    session_id: UUID,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    request: Request,
    user: OptionalUserDep,
) -> StreamingResponse:
    if nimbusware_collab_enabled():
        require_collab_enabled()
        _session_or_404(chat_store, session_id)
        actor = actor_user_id(request, user)
        require_session_participant(
            collab_store,
            session_id=session_id,
            user_id=actor,
            minimum_role="session_read",
        )
    else:
        _session_or_404(chat_store, session_id)

    async def generate() -> Any:
        last_updated: str | None = None
        idle = 0
        while idle < 30:
            session = chat_store.get_session(session_id)
            if session is None:
                yield _sse_pack("error", {"code": "chat_session_not_found"})
                return
            updated = session.updated_at.isoformat()
            if updated != last_updated:
                last_updated = updated
                idle = 0
                turns = chat_store.list_turns(session_id)
                theater = [
                    t.to_dict()
                    for t in turns
                    if t.role in {"theater", "run_status", "participant"}
                ][-12:]
                yield _sse_pack(
                    "session",
                    {
                        "session_id": str(session_id),
                        "updated_at": updated,
                        "theater_lines": theater,
                    },
                )
            else:
                idle += 1
                yield _sse_pack("heartbeat", {"session_id": str(session_id)})
            await asyncio.sleep(1.0)
        yield _sse_pack("done", {"session_id": str(session_id), "reason": "idle_timeout"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
