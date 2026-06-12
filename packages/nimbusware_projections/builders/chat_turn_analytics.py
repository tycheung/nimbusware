from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from nimbusware_maker.chat_models import ChatTurnRecord
from nimbusware_maker.chat_store import child_turn_ids, path_to_root


def _parse_ts(raw: object) -> datetime | None:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, str) and raw.strip():
        text = raw.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _turns_by_session(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        sid = str(row.get("session_id") or "")
        if sid:
            grouped[sid].append(row)
    for session_rows in grouped.values():
        session_rows.sort(key=lambda r: int(r.get("ordinal") or 0))
    return grouped


def _row_to_turn(row: dict[str, Any]) -> ChatTurnRecord | None:
    tid = row.get("turn_id")
    sid = row.get("session_id")
    if tid is None or sid is None:
        return None
    parent = row.get("parent_turn_id")
    posted = _parse_ts(row.get("posted_at"))
    raw_payload = row.get("payload")
    payload: dict[str, Any] = dict(raw_payload) if isinstance(raw_payload, dict) else {}
    return ChatTurnRecord(
        turn_id=UUID(str(tid)),
        session_id=UUID(str(sid)),
        parent_turn_id=UUID(str(parent)) if parent else None,
        ordinal=int(row.get("ordinal") or 0),
        role=str(row.get("role") or ""),
        text=str(row.get("text") or ""),
        payload=payload,
        work_type=str(row["work_type"]) if row.get("work_type") else None,
        work_type_source=(str(row["work_type_source"]) if row.get("work_type_source") else None),
        run_id=UUID(str(row["run_id"])) if row.get("run_id") else None,
        campaign_id=UUID(str(row["campaign_id"])) if row.get("campaign_id") else None,
        event_seq=int(row["event_seq"]) if row.get("event_seq") is not None else None,
        posted_at=posted or datetime.now(timezone.utc),
    )


def _max_branch_depth(session_rows: list[dict[str, Any]]) -> int:
    turns: dict[UUID, ChatTurnRecord] = {}
    for row in session_rows:
        turn = _row_to_turn(row)
        if turn is not None:
            turns[turn.turn_id] = turn
    if not turns:
        return 0

    def depth(leaf_id: UUID) -> int:
        return len(path_to_root(turns, leaf_id))

    leaves = [tid for tid in turns if not child_turn_ids(turns, tid)]
    return max((depth(leaf) for leaf in leaves), default=0)


def build_chat_turn_summary(
    turn_rows: list[dict[str, Any]],
    *,
    limit_sessions: int,
) -> dict[str, Any]:
    by_session = _turns_by_session(turn_rows)
    sessions_scanned = len(by_session)
    role_counts: dict[str, int] = defaultdict(int)
    classifier_starts = 0
    override_starts = 0
    fork_events = 0
    sessions_with_run = 0
    branch_depths: list[int] = []

    for _sid, session_rows in by_session.items():
        has_run = any(r.get("run_id") for r in session_rows)
        if has_run:
            sessions_with_run += 1
        branch_depths.append(_max_branch_depth(session_rows))
        parent_children: dict[str, int] = defaultdict(int)
        for row in session_rows:
            role = str(row.get("role") or "")
            role_counts[role] += 1
            parent = row.get("parent_turn_id")
            if parent is not None:
                parent_children[str(parent)] += 1
            if role == "run_status":
                source = str(row.get("work_type_source") or "").strip().lower()
                if source == "classifier":
                    classifier_starts += 1
                elif source == "operator_override":
                    override_starts += 1
        fork_events += sum(1 for count in parent_children.values() if count > 1)

    start_total = classifier_starts + override_starts
    acceptance_rate = classifier_starts / start_total if start_total else None
    generated = datetime.now(timezone.utc).isoformat()
    return {
        "generated_at": generated,
        "limit_sessions": limit_sessions,
        "sessions_scanned": sessions_scanned,
        "turn_count": len(turn_rows),
        "role_counts": dict(role_counts),
        "classifier_start_count": classifier_starts,
        "override_start_count": override_starts,
        "classifier_acceptance_rate": acceptance_rate,
        "target_rate": 0.70,
        "meets_target": acceptance_rate is not None and acceptance_rate >= 0.70,
        "fork_branch_count": fork_events,
        "sessions_with_run_id": sessions_with_run,
        "max_branch_depth": max(branch_depths) if branch_depths else 0,
        "mean_branch_depth": (sum(branch_depths) / len(branch_depths) if branch_depths else None),
        "snapshot": True,
    }
