from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.deps import ChatStoreDep, CollabStoreDep, StoreDep
from api.routes.auth import OptionalUserDep
from api.routes.chat_common import actor_user_id, require_collab_enabled
from api.routes.chat_service import session_or_404
from api.schemas.openapi import PROBLEM_RESPONSE_404
from api.schemas.peel_responses import (
    SseStreamErrorResponse,
    llm_json_openapi_responses,
    with_long_tail_peel_503,
)
from api.sse_peel import (
    early_llm_sse_peel_miss,
    sse_error_envelope,
    sse_pack,
    sse_stream_openapi_responses,
)
from api.user import UserDep
from auth.permissions import enforce_collab_turn_write, require_session_participant
from env.env_flags import nimbusware_collab_enabled
from orchestrator.collab.stream_redaction import redact_theater_lines

router = APIRouter(prefix="/chat", tags=["maker"])

_SESSION_SSE_CAP = 96
_STREAM_ROLES = frozenset({"theater", "run_status", "participant", "user", "system"})


def _participant_signature(collab_store: CollabStoreDep, session_id: UUID) -> str:
    rows = collab_store.list_participants(session_id)
    bits = sorted(f"{p.user_id}:{p.role}" for p in rows)
    return "|".join(bits)


@router.get(
    "/sessions/{session_id}/stream",
    responses={
        **sse_stream_openapi_responses(
            miss_model=SseStreamErrorResponse,
            not_found=PROBLEM_RESPONSE_404,
        ),
        **llm_json_openapi_responses(),  # sak496-g / sak515-i
    },
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
        session_or_404(chat_store, session_id)
        actor = actor_user_id(request, user)
        require_session_participant(
            collab_store,
            session_id=session_id,
            user_id=actor,
            minimum_role="session_read",
        )
    else:
        session_or_404(chat_store, session_id)

    async def generate() -> Any:
        if peel := early_llm_sse_peel_miss(feature="chat_session_stream"):  # sak496-g
            yield peel
            return
        last_fingerprint: str | None = None
        idle = 0
        while idle < 60:
            session = chat_store.get_session(session_id)
            if session is None:
                yield sse_error_envelope(
                    feature="chat_session_stream",
                    error="chat session not found",
                    via="local",
                    status="error",
                )
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
                if nimbusware_collab_enabled():
                    lines = redact_theater_lines(lines)
                yield sse_pack(
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
                yield sse_pack("heartbeat", {"session_id": str(session_id)})
            await asyncio.sleep(0.5)
        yield sse_pack("done", {"session_id": str(session_id), "reason": "idle_timeout"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class CommentaryBody(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class CommentaryResponse(BaseModel):
    """POST /chat/sessions/{id}/commentary (`sak482-e`)."""

    model_config = {"extra": "allow"}

    turn: dict[str, Any] | None = None
    discipline_routes: list[dict[str, str]] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.post(
    "/sessions/{session_id}/commentary",
    response_model=CommentaryResponse,
    summary="Post session commentary (`sak482-e`)",
    responses=with_long_tail_peel_503({404: PROBLEM_RESPONSE_404}),  # sak516-a
)
def post_session_commentary(
    session_id: UUID,
    body: CommentaryBody,
    request: Request,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    store: StoreDep,
    user: OptionalUserDep,
    _user: UserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    session_or_404(chat_store, session_id)
    actor_id = user.user_id if user is not None else actor_user_id(request, user)
    enforce_collab_turn_write(
        collab_store,
        session_id=session_id,
        user_id=actor_id,
        collab_enabled=True,
    )
    turn = chat_store.append_turn(
        session_id,
        role="participant",
        text=body.text.strip(),
        payload={"kind": "commentary"},
    )
    routes: list[dict[str, str]] = []
    if nimbusware_collab_enabled():
        from maker.collab.discipline_routing import maybe_route_collab_message

        routes = maybe_route_collab_message(
            store,
            chat_store,
            collab_store,
            session_id=session_id,
            message=body.text.strip(),
            actor_user_id=actor_id,
        )
    result: dict[str, Any] = {"turn": turn.to_dict()}
    if routes:
        result["discipline_routes"] = routes
    return result
