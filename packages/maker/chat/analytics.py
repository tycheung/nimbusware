from __future__ import annotations

from typing import Any
from uuid import UUID

from maker.chat.session_models import ChatTurnRecord


def _turn_analytics_row(turn: ChatTurnRecord, *, project_id: UUID) -> dict[str, Any]:
    return {
        "turn_id": str(turn.turn_id),
        "session_id": str(turn.session_id),
        "parent_turn_id": str(turn.parent_turn_id) if turn.parent_turn_id else None,
        "ordinal": turn.ordinal,
        "role": turn.role,
        "text": turn.text,
        "payload": turn.payload,
        "work_type": turn.work_type,
        "work_type_source": turn.work_type_source,
        "run_id": str(turn.run_id) if turn.run_id else None,
        "campaign_id": str(turn.campaign_id) if turn.campaign_id else None,
        "event_seq": turn.event_seq,
        "posted_at": turn.posted_at.isoformat() if turn.posted_at else None,
        "project_id": str(project_id),
    }


def _in_memory_analytics_rows(
    store: Any,
    *,
    limit_sessions: int,
) -> list[dict[str, Any]]:
    cap = max(1, min(limit_sessions, 5000))
    sessions = sorted(
        store._sessions.values(),
        key=lambda s: s.updated_at,
        reverse=True,
    )[:cap]
    out: list[dict[str, Any]] = []
    for session in sessions:
        turns = sorted(
            store._turns[session.session_id].values(),
            key=lambda t: t.ordinal,
        )
        for turn in turns:
            out.append(_turn_analytics_row(turn, project_id=session.project_id))
    return out
