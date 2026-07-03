from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from orchestrator.interjection_queue import (
    InterjectionPriority,
    _normalize_surface_id,
    _parse_surface_steer_prefix,
    queue_for_run,
)

_SURFACE_MENTION_RE = re.compile(r"@([a-zA-Z][\w-]*)")


def normalize_surface_id(raw: str) -> str | None:
    return _normalize_surface_id(raw)


def parse_surface_mentions(message: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in _SURFACE_MENTION_RE.findall(str(message or "")):
        surface_id = normalize_surface_id(match)
        if surface_id and surface_id not in seen:
            seen.add(surface_id)
            out.append(surface_id)
    return out


def parse_surface_steer_prefix(message: str) -> tuple[str, str | None]:
    return _parse_surface_steer_prefix(message)


def surface_steer_routes(message: str) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    for surface_id in parse_surface_mentions(message):
        routes.append({"surface_id": surface_id, "source": "mention"})
    _, prefix_surface = parse_surface_steer_prefix(message)
    if prefix_surface and not any(r["surface_id"] == prefix_surface for r in routes):
        routes.append({"surface_id": prefix_surface, "source": "steer_prefix"})
    return routes


def enqueue_surface_steers(
    store: Any,
    *,
    run_id: UUID | str,
    message: str,
    routed_from_user_id: str | None = None,
) -> list[dict[str, str]]:
    from orchestrator.slice.interjection import emit_interjection_enqueued

    routes = surface_steer_routes(message)
    if not routes:
        return []
    body, prefix_surface = parse_surface_steer_prefix(message)
    q = queue_for_run(str(run_id))
    enqueued: list[dict[str, str]] = []
    for route in routes:
        surface_id = route["surface_id"]
        steer_body = body if prefix_surface == surface_id else message.strip()
        tagged = f"[steer:{surface_id}] {steer_body}".strip()
        item = q.enqueue(
            tagged,
            priority=InterjectionPriority.NEXT,
            steer_from_chat=True,
            surface_id=surface_id,
            routed_from_user_id=routed_from_user_id,
        )
        emit_interjection_enqueued(store, run_id, item)
        enqueued.append(dict(route))
    return enqueued
