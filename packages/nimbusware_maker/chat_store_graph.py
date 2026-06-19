from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from nimbusware_maker.chat_models import CHAT_TURN_ROLES, ChatSessionRecord, ChatTurnRecord


def _validate_role(role: str) -> str:
    r = role.strip().lower()
    if r not in CHAT_TURN_ROLES:
        msg = f"invalid chat turn role: {role!r}"
        raise ValueError(msg)
    return r


def path_to_root(turns: dict[UUID, ChatTurnRecord], leaf_id: UUID) -> list[ChatTurnRecord]:
    path: list[ChatTurnRecord] = []
    cur: UUID | None = leaf_id
    seen: set[UUID] = set()
    while cur is not None:
        if cur in seen:
            break
        seen.add(cur)
        turn = turns.get(cur)
        if turn is None:
            break
        path.append(turn)
        cur = turn.parent_turn_id
    path.reverse()
    return path


def child_turn_ids(turns: dict[UUID, ChatTurnRecord], parent_id: UUID) -> list[UUID]:
    kids = [t.turn_id for t in turns.values() if t.parent_turn_id == parent_id]
    return sorted(kids, key=lambda tid: turns[tid].ordinal)


def sibling_count(turns: dict[UUID, ChatTurnRecord], turn_id: UUID) -> int:
    turn = turns.get(turn_id)
    if turn is None or turn.parent_turn_id is None:
        return 0
    return len(child_turn_ids(turns, turn.parent_turn_id))


def leaf_descendants(turns: dict[UUID, ChatTurnRecord], ancestor_id: UUID) -> list[UUID]:
    children_map: dict[UUID, list[UUID]] = defaultdict(list)
    for t in turns.values():
        if t.parent_turn_id is not None:
            children_map[t.parent_turn_id].append(t.turn_id)

    def is_ancestor_of(leaf: UUID, ancestor: UUID) -> bool:
        cur: UUID | None = leaf
        seen: set[UUID] = set()
        while cur is not None:
            if cur == ancestor:
                return True
            if cur in seen:
                return False
            seen.add(cur)
            node = turns.get(cur)
            if node is None:
                return False
            cur = node.parent_turn_id
        return False

    leaves = [tid for tid in turns if not children_map.get(tid)]
    return [lid for lid in leaves if is_ancestor_of(lid, ancestor_id)]


def build_graph(session: ChatSessionRecord, turns: dict[UUID, ChatTurnRecord]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for turn in sorted(turns.values(), key=lambda t: t.ordinal):
        siblings = sibling_count(turns, turn.turn_id)
        node = turn.to_dict()
        node["child_count"] = len(child_turn_ids(turns, turn.turn_id))
        node["sibling_count"] = siblings
        node["is_active_path"] = False
        nodes.append(node)
        if turn.parent_turn_id is not None:
            edges.append(
                {
                    "from_turn_id": str(turn.parent_turn_id),
                    "to_turn_id": str(turn.turn_id),
                }
            )
    if session.active_leaf_turn_id:
        active_ids = {str(t.turn_id) for t in path_to_root(turns, session.active_leaf_turn_id)}
        for node in nodes:
            if node["turn_id"] in active_ids:
                node["is_active_path"] = True
    branches: list[dict[str, Any]] = []
    for turn in turns.values():
        if turn.parent_turn_id is None:
            continue
        sibs = child_turn_ids(turns, turn.parent_turn_id)
        if len(sibs) > 1:
            branches.append(
                {
                    "parent_turn_id": str(turn.parent_turn_id),
                    "child_turn_ids": [str(x) for x in sibs],
                }
            )
    return {
        "session_id": str(session.session_id),
        "active_leaf_turn_id": (
            str(session.active_leaf_turn_id) if session.active_leaf_turn_id else None
        ),
        "nodes": nodes,
        "edges": edges,
        "branches": branches,
    }


def turns_to_legacy_messages(turns: list[ChatTurnRecord]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for turn in turns:
        if turn.role == "user":
            out.append(
                {
                    "role": "user",
                    "text": turn.text,
                    "attachments": turn.payload.get("attachments") or [],
                    "posted_at": turn.posted_at.isoformat() if turn.posted_at else None,
                    "turn_id": str(turn.turn_id),
                }
            )
        elif turn.role in {
            "system",
            "classifier",
            "work_type_switch",
            "run_status",
            "theater",
            "participant",
        }:
            kind = "participant" if turn.role == "participant" else turn.role
            out.append(
                {
                    "role": "participant" if turn.role == "participant" else "system",
                    "text": turn.text,
                    "turn_id": str(turn.turn_id),
                    "kind": kind,
                    "posted_at": turn.posted_at.isoformat() if turn.posted_at else None,
                }
            )
    return out
