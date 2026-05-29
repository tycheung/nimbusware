"""Map between DB rows and `validate_event_dict` input shapes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from agent_core.models import HermesEventUnion


def event_row_from_serialized(full: dict[str, Any]) -> dict[str, Any]:
    """Split `serialize_event_persistent` output into DB column dict."""
    return {
        "event_id": full["event_id"],
        "run_id": full["run_id"],
        "stage_id": full.get("stage_id"),
        "task_id": full.get("task_id"),
        "event_type": full["event_type"],
        "event_version": full.get("event_version", 1),
        "occurred_at": full["occurred_at"],
        "actor_role": full.get("actor_role"),
        "model_id": full.get("model_id"),
        "correlation_id": full.get("correlation_id"),
        "causation_id": full.get("causation_id"),
        "payload": full["payload"],
        "metadata": full.get("metadata") or {},
    }


def serialized_event_from_row(row: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct dict for `validate_event_dict` from a SELECT row."""
    occurred = row["occurred_at"]
    if isinstance(occurred, datetime):
        occurred = occurred.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    base: dict[str, Any] = {
        "event_id": str(row["event_id"]),
        "run_id": str(row["run_id"]),
        "occurred_at": occurred,
        "event_type": row["event_type"],
        "event_version": int(row.get("event_version") or 1),
        "payload": row["payload"],
        "metadata": row.get("metadata") or {},
    }
    if row.get("stage_id") is not None:
        base["stage_id"] = str(row["stage_id"])
    if row.get("task_id") is not None:
        base["task_id"] = str(row["task_id"])
    if row.get("actor_role") is not None:
        base["actor_role"] = str(row["actor_role"])
    if row.get("model_id") is not None:
        base["model_id"] = str(row["model_id"])
    if row.get("correlation_id") is not None:
        base["correlation_id"] = str(row["correlation_id"])
    if row.get("causation_id") is not None:
        base["causation_id"] = str(row["causation_id"])
    return base


@runtime_checkable
class EventStore(Protocol):
    def append(self, event: HermesEventUnion) -> int:
        """Persist validated event; return store_seq."""

    def list_run_events(self, run_id: str) -> list[dict[str, Any]]:
        """Rows ordered by store_seq (for replay / API)."""

    def list_run_events_many(self, run_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        """Batch rows by ``run_id`` for bounded multi-run replay reads."""

    def get_run_head(self, run_id: str) -> dict[str, Any] | None:
        """Latest row for run or None."""

    def find_run_id_for_run_created_correlation(self, correlation_id: UUID) -> UUID | None:
        """Return ``run_id`` if a ``run.created`` row exists with this ``correlation_id``."""

    def max_store_seq_for_run(self, run_id: str) -> int | None:
        """Maximum ``store_seq`` for ``run_id``, or ``None`` if the run has no rows."""

    def list_recent_run_ids(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        workflow_profile: str | None = None,
        workflow_profile_prefix: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        has_escalation: bool | None = None,
        list_status: str | None = None,
        order: str = "newest_first",
    ) -> list[UUID]:
        """Distinct ``run_id`` values ordered by latest ``store_seq`` per run.

        When ``workflow_profile`` is set, restrict to an exact first ``run.created`` profile match
        (case-insensitive); ``workflow_profile_prefix`` is ignored in that case.

        Otherwise ``workflow_profile_prefix`` filters case-insensitive prefix on profile.

        ``order`` is ``newest_first`` (default) or ``oldest_first`` (by last ``store_seq``).

        ``created_after`` / ``created_before`` filter on first ``run.created`` ``occurred_at``.

        When ``has_escalation`` is set, restrict to runs that have (``True``) or lack (``False``) a
        ``run.escalated`` event.

        When ``list_status`` is set, restrict to runs whose replay list status matches (same
        strings as ``build_run_summary`` / ``GET /v1/runs`` ``status`` query: ``created``,
        ``running``, ``terminal``).
        """

    def count_recent_runs(
        self,
        *,
        workflow_profile: str | None = None,
        workflow_profile_prefix: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        has_escalation: bool | None = None,
        list_status: str | None = None,
    ) -> int:
        """Count runs matching ``list_recent_run_ids`` filters (ignores limit/offset/order)."""

    def list_recent_run_rows_cursor(
        self,
        *,
        limit: int,
        cursor_after_seq: int,
        cursor_after_run_id: UUID,
        workflow_profile: str | None = None,
        workflow_profile_prefix: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        has_escalation: bool | None = None,
        list_status: str | None = None,
        order: str = "newest_first",
    ) -> tuple[list[tuple[UUID, int]], bool]:
        """Keyset page after the given run's activity head.

        Uses ``cursor_after_seq`` and ``cursor_after_run_id`` (last row of the prior page).
        Ordering matches ``list_recent_run_ids`` (``newest_first`` / ``oldest_first`` by max
        ``store_seq`` per run, then ``run_id`` as a stable tiebreaker). Returns at most ``limit``
        rows and whether a further page exists (fetched with ``limit + 1`` internally).
        """
