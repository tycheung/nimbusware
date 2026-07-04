from __future__ import annotations

from typing import Any


IMPLEMENT_ROLE = "backend_writer"
IMPLEMENT_FORBIDDEN_CONTEXT = frozenset(
    {"chat_transcript", "planner_exploration", "theater_dump"},
)


def roles_receiving_chat_history() -> dict[str, bool]:
    """Audit map: which agent roles may receive chat session history today."""
    return {
        "chat_assistant": True,
        "collab_host": True,
        IMPLEMENT_ROLE: False,
        "planner": False,
        "critic": False,
    }


def implement_context_sources() -> frozenset[str]:
    """Allowed context sources for slice implement agent."""
    return frozenset(
        {
            "slice.plan",
            "slice.handoff",
            "memory.index",
            "memory.fetch",
            "operator.steer",
            "failure.learning",
        },
    )


def filter_implement_context(payload: dict[str, Any]) -> dict[str, Any]:
    """Strip disallowed keys before implement-role prompt assembly."""
    blocked = IMPLEMENT_FORBIDDEN_CONTEXT
    return {k: v for k, v in payload.items() if k not in blocked}


def artifact_only_handoff_enabled() -> bool:
    from env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_IMPLEMENT_ARTIFACT_HANDOFF", default=True)
