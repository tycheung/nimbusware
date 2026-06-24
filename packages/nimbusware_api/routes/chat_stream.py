from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from nimbusware_api.deps import ChatStoreDep, CollabStoreDep
from nimbusware_api.routes.auth import OptionalUserDep
from nimbusware_api.routes.chat_collab_common import actor_user_id, require_collab_enabled
from nimbusware_api.routes.chat_common import session_or_404 as _session_or_404
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_auth.permissions import require_session_participant
from nimbusware_env.env_flags import nimbusware_collab_enabled

router = APIRouter(prefix="/chat", tags=["maker"])

_SESSION_SSE_CAP = 96
_STREAM_ROLES = frozenset({"theater", "run_status", "participant", "user", "system"})


def _sse_pack(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _participant_signature(collab_store: CollabStoreDep, session_id: UUID) -> str:
    rows = collab_store.list_participants(session_id)
    bits = sorted(f"{p.user_id}:{p.role}" for p in rows)
    return "|".join(bits)


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
        last_fingerprint: str | None = None
        idle = 0
        while idle < 60:
            session = chat_store.get_session(session_id)
            if session is None:
                yield _sse_pack("error", {"code": "chat_session_not_found"})
                return
            turns = chat_store.list_turns(session_id)
            turn_count = len(turns)
            updated = session.updated_at.isoformat()
            part_sig = ""
            participants: list[dict[str, Any]] = []
            if nimbusware_collab_enabled():
                part_sig = _participant_signature(collab_store, session_id)
                participants = [p.to_dict() for p in collab_store.list_participants(session_id)]
            fingerprint = f"{updated}:{turn_count}:{part_sig}"
            if fingerprint != last_fingerprint:
                last_fingerprint = fingerprint
                idle = 0
                lines = [t.to_dict() for t in turns if t.role in _STREAM_ROLES][-_SESSION_SSE_CAP:]
                yield _sse_pack(
                    "session",
                    {
                        "session_id": str(session_id),
                        "updated_at": updated,
                        "turn_count": turn_count,
                        "theater_lines": lines,
                        "participants": participants,
                    },
                )
            else:
                idle += 1
                yield _sse_pack("heartbeat", {"session_id": str(session_id)})
            await asyncio.sleep(0.5)
        yield _sse_pack("done", {"session_id": str(session_id), "reason": "idle_timeout"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
