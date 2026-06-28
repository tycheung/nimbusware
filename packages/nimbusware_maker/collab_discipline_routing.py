from __future__ import annotations

from typing import Any
from uuid import UUID

from nimbusware_maker.collab_disciplines import discipline_routes


def enqueue_collab_discipline_routes(
    store: Any,
    *,
    run_id: UUID,
    message: str,
    actor_user_id: str | None = None,
    participant_discipline: str | None = None,
) -> list[dict[str, str]]:
    from nimbusware_orchestrator.interjection_queue import InterjectionPriority, queue_for_run
    from nimbusware_orchestrator.slice_interjection import emit_interjection_enqueued

    routes = discipline_routes(message, participant_discipline=participant_discipline)
    if not routes:
        return []
    q = queue_for_run(str(run_id))
    enqueued: list[dict[str, str]] = []
    for route in routes:
        tagged = (
            f"[{route['taxonomy_key']}] {message.strip()}"
            if message.strip()
            else f"[{route['taxonomy_key']}]"
        )
        item = q.enqueue(
            tagged,
            priority=InterjectionPriority.NEXT,
            discipline=route["discipline"],
            taxonomy_key=route["taxonomy_key"],
            routed_from_user_id=actor_user_id,
        )
        emit_interjection_enqueued(store, run_id, item)
        enqueued.append(dict(route))
    return enqueued


def _actor_display_name(collab_store: Any, session_id: UUID, actor_user_id: UUID | None) -> str:
    if actor_user_id is None:
        return "operator"
    participant = collab_store.get_participant(session_id, actor_user_id)
    if participant is None:
        return str(actor_user_id)[:8]
    return participant.display_name or participant.username or str(actor_user_id)[:8]


def append_routed_feedback_turns(
    chat_store: Any,
    collab_store: Any,
    *,
    session_id: UUID,
    message: str,
    actor_user_id: UUID | None,
    routes: list[dict[str, str]],
) -> None:
    if not routes:
        return
    actor = _actor_display_name(collab_store, session_id, actor_user_id)
    excerpt = message.strip()[:240]
    for route in routes:
        taxonomy_key = route.get("taxonomy_key") or route.get("discipline") or "agent"
        chat_store.append_turn(
            session_id,
            role="participant",
            text=f"{actor} → {taxonomy_key}: {excerpt}",
            payload={
                "kind": "discipline_route",
                "discipline": route.get("discipline"),
                "taxonomy_key": taxonomy_key,
                "routed_from_user_id": str(actor_user_id) if actor_user_id else None,
                "source": route.get("source"),
            },
        )


def maybe_route_collab_message(
    store: Any,
    chat_store: Any,
    collab_store: Any,
    *,
    session_id: UUID,
    message: str,
    actor_user_id: UUID | None,
) -> list[dict[str, str]]:
    session = chat_store.get_session(session_id)
    if session is None or session.run_id is None:
        return []
    participant_discipline: str | None = None
    if actor_user_id is not None:
        participant = collab_store.get_participant(session_id, actor_user_id)
        if participant is not None and getattr(participant, "user_discipline", None):
            participant_discipline = str(participant.user_discipline)
    routes = enqueue_collab_discipline_routes(
        store,
        run_id=session.run_id,
        message=message,
        actor_user_id=str(actor_user_id) if actor_user_id is not None else None,
        participant_discipline=participant_discipline,
    )
    from nimbusware_orchestrator.surface_interjection_routing import enqueue_surface_steers

    surface_routes = enqueue_surface_steers(
        store,
        run_id=session.run_id,
        message=message,
        routed_from_user_id=str(actor_user_id) if actor_user_id is not None else None,
    )
    routes.extend(surface_routes)
    append_routed_feedback_turns(
        chat_store,
        collab_store,
        session_id=session_id,
        message=message,
        actor_user_id=actor_user_id,
        routes=routes,
    )
    return routes
