from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.deps import ChatStoreDep, CollabStoreDep, StoreDep
from api.errors import problem
from api.routes.auth import OptionalUserDep
from api.routes.chat_common import actor_user_id
from api.schemas.openapi import PROBLEM_RESPONSE_404
from auth.permissions import require_session_participant
from env.env_flags import nimbusware_collab_enabled
from maker.collab.discipline_routing import enqueue_collab_discipline_routes
from maker.collab.disciplines import parse_discipline_mentions
from orchestrator.interjection_queue import InterjectionPriority, queue_for_run
from orchestrator.slice.interjection import emit_interjection_enqueued
from orchestrator.surface_interjection_routing import (
    enqueue_surface_steers,
    surface_steer_routes,
)

router = APIRouter()


class InterjectionEnqueueBody(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    priority: str = "next"
    force_break: bool = False


class InterjectionQueueResponse(BaseModel):
    run_id: str
    queue: dict[str, Any] = Field(default_factory=dict)


def _enforce_interjection_collab(
    *,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    run_id: UUID,
    request: Request,
    user: OptionalUserDep,
) -> None:
    if not nimbusware_collab_enabled():
        return
    session = chat_store.find_session_by_run_id(run_id)
    if session is None:
        return
    actor = actor_user_id(request, user)
    require_session_participant(
        collab_store,
        session_id=session.session_id,
        user_id=actor,
        minimum_role="session_write",
    )


@router.get(
    "/runs/{run_id}/interjection-queue",
    response_model=InterjectionQueueResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_interjection_queue(run_id: UUID, store: StoreDep) -> InterjectionQueueResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    q = queue_for_run(str(run_id))
    return InterjectionQueueResponse(run_id=str(run_id), queue=q.to_dict())


@router.post(
    "/runs/{run_id}/interjection-queue",
    response_model=InterjectionQueueResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def post_interjection_enqueue(
    run_id: UUID,
    body: InterjectionEnqueueBody,
    request: Request,
    store: StoreDep,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    user: OptionalUserDep,
) -> InterjectionQueueResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    _enforce_interjection_collab(
        chat_store=chat_store,
        collab_store=collab_store,
        run_id=run_id,
        request=request,
        user=user,
    )
    priority = (
        InterjectionPriority.LAST
        if body.priority.strip().lower() == "last"
        else InterjectionPriority.NEXT
    )
    q = queue_for_run(str(run_id))

    if parse_discipline_mentions(body.message):
        actor = actor_user_id(request, user)
        routes = enqueue_collab_discipline_routes(
            store,
            run_id=run_id,
            message=body.message,
            actor_user_id=str(actor) if actor is not None else None,
        )
        if routes:
            return InterjectionQueueResponse(run_id=str(run_id), queue=q.to_dict())

    routes = surface_steer_routes(body.message)
    mention_only = bool(routes) and all(r.get("source") == "mention" for r in routes)
    if mention_only:
        actor = actor_user_id(request, user)
        enqueue_surface_steers(
            store,
            run_id=run_id,
            message=body.message,
            routed_from_user_id=str(actor) if actor is not None else None,
        )
        return InterjectionQueueResponse(run_id=str(run_id), queue=q.to_dict())
    item = q.enqueue(
        body.message,
        priority=priority,
        force_break=body.force_break,
    )
    emit_interjection_enqueued(store, run_id, item)
    return InterjectionQueueResponse(run_id=str(run_id), queue=q.to_dict())
