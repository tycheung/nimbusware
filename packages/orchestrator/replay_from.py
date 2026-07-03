from __future__ import annotations

from dataclasses import dataclass
from typing import Any

REPLAY_STAGE_NAME = "run.replay.started"


@dataclass(frozen=True)
class ReplayPolicy:
    compact_enabled: bool = True
    ignore_compaction_ids: tuple[str, ...] = ()
    ignore_revert_ids: tuple[str, ...] = ()


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("payload")
    return dict(raw) if isinstance(raw, dict) else {}


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("metadata")
    return dict(raw) if isinstance(raw, dict) else {}


def active_replay_policy(events: list[dict[str, Any]]) -> ReplayPolicy | None:
    latest_seq = -1
    meta: dict[str, Any] | None = None
    for row in events:
        if _payload(row).get("stage_name") != REPLAY_STAGE_NAME:
            continue
        seq = int(row.get("store_seq") or 0)
        if seq >= latest_seq:
            latest_seq = seq
            meta = _metadata(row)
    if meta is None:
        return None
    policy_raw = meta.get("replay_policy")
    if not isinstance(policy_raw, dict):
        return ReplayPolicy()
    ignore_c = policy_raw.get("ignore_compaction_ids")
    ignore_r = policy_raw.get("ignore_revert_ids")
    compact = policy_raw.get("compact_enabled", True)
    return ReplayPolicy(
        compact_enabled=bool(compact),
        ignore_compaction_ids=tuple(
            str(x).strip()
            for x in (ignore_c if isinstance(ignore_c, list) else [])
            if str(x).strip()
        ),
        ignore_revert_ids=tuple(
            str(x).strip()
            for x in (ignore_r if isinstance(ignore_r, list) else [])
            if str(x).strip()
        ),
    )


def compaction_skipped_compaction_ids(events: list[dict[str, Any]]) -> set[str]:
    policy = active_replay_policy(events)
    if policy is None:
        return set()
    return set(policy.ignore_compaction_ids)


def effective_reverted_compaction_ids(events: list[dict[str, Any]]) -> set[str]:
    from orchestrator.context_compaction import reverted_compaction_ids

    reverted = reverted_compaction_ids(events)
    policy = active_replay_policy(events)
    if policy is None:
        return reverted
    for rid in policy.ignore_revert_ids:
        reverted.discard(rid)
    return reverted


def compaction_allowed(events: list[dict[str, Any]]) -> bool:
    policy = active_replay_policy(events)
    if policy is None:
        return True
    return policy.compact_enabled


def emit_replay_started_event(
    store: object,
    *,
    run_id: object,
    from_store_seq: int,
    replay_policy: ReplayPolicy,
    operator_ack: bool,
    reason: str = "",
) -> None:
    from datetime import datetime, timezone
    from uuid import uuid4

    from agent_core.models import EventType, StageStartedEvent, StageStartedPayload

    store.append(  # type: ignore[attr-defined]
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,  # type: ignore[arg-type]
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "from_store_seq": int(from_store_seq),
                "operator_ack": bool(operator_ack),
                "reason": reason[:500] if reason else "",
                "replay_policy": {
                    "compact_enabled": replay_policy.compact_enabled,
                    "ignore_compaction_ids": list(replay_policy.ignore_compaction_ids),
                    "ignore_revert_ids": list(replay_policy.ignore_revert_ids),
                },
            },
            payload=StageStartedPayload(stage_name=REPLAY_STAGE_NAME, attempt=1),
        ),
    )
