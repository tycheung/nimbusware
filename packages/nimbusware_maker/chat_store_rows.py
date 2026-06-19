from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nimbusware_maker.chat_models import ChatSessionRecord, ChatTurnRecord


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


_UNSET: Any = object()


def _session_from_row(row: dict[str, object]) -> ChatSessionRecord:
    meta = row.get("metadata")
    raw_tags = row.get("tags")
    tags: tuple[str, ...] = (
        tuple(str(t) for t in raw_tags) if isinstance(raw_tags, (list, tuple)) else ()
    )
    return ChatSessionRecord(
        session_id=row["session_id"],  # type: ignore[arg-type]
        project_id=row["project_id"],  # type: ignore[arg-type]
        tenant_id=row["tenant_id"],  # type: ignore[arg-type]
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
        title=str(row["title"]) if row.get("title") else None,
        root_turn_id=row.get("root_turn_id"),  # type: ignore[arg-type]
        active_leaf_turn_id=row.get("active_leaf_turn_id"),  # type: ignore[arg-type]
        last_classification=row.get("last_classification"),  # type: ignore[arg-type]
        work_type_override=(
            str(row["work_type_override"]) if row.get("work_type_override") else None
        ),
        run_id=row.get("run_id"),  # type: ignore[arg-type]
        campaign_id=row.get("campaign_id"),  # type: ignore[arg-type]
        host_user_id=row.get("host_user_id"),  # type: ignore[arg-type]
        workload_distribution=str(row.get("workload_distribution") or "host_only"),
        folder_id=row.get("folder_id"),  # type: ignore[arg-type]
        tags=tags,
        metadata=dict(meta) if isinstance(meta, dict) else {},
    )


def _turn_from_row(row: dict[str, object]) -> ChatTurnRecord:
    raw_seq = row.get("event_seq")
    event_seq = int(str(raw_seq)) if raw_seq is not None else None
    return ChatTurnRecord(
        turn_id=row["turn_id"],  # type: ignore[arg-type]
        session_id=row["session_id"],  # type: ignore[arg-type]
        parent_turn_id=row.get("parent_turn_id"),  # type: ignore[arg-type]
        ordinal=int(str(row["ordinal"])),
        role=str(row["role"]),
        text=str(row["text"]),
        payload=row["payload"],  # type: ignore[arg-type]
        work_type=str(row["work_type"]) if row.get("work_type") else None,
        work_type_source=(str(row["work_type_source"]) if row.get("work_type_source") else None),
        run_id=row.get("run_id"),  # type: ignore[arg-type]
        campaign_id=row.get("campaign_id"),  # type: ignore[arg-type]
        event_seq=event_seq,
        posted_at=row["posted_at"],  # type: ignore[arg-type]
    )
