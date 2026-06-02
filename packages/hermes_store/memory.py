from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from agent_core.models import HermesEventUnion, validate_event_dict
from hermes_store.allowed_types import assert_event_type_registered
from hermes_store.protocol import event_row_from_serialized, serialized_event_from_row
from hermes_store.tenant_scope import store_tenant_id
from nimbusware_iam.constants import DEFAULT_TENANT_ID


def _json_safe(obj: Any) -> Any:
    return json.loads(json.dumps(obj, default=str))


class InMemoryEventStore:
    """Append-only store for unit tests and local dev without Postgres."""

    def __init__(self) -> None:
        self._rows: list[dict[str, Any]] = []
        self._seq = 0

    def _scoped_rows(self) -> list[dict[str, Any]]:
        tid = store_tenant_id()
        return [r for r in self._rows if r.get("tenant_id", DEFAULT_TENANT_ID) == tid]

    def append(self, event: HermesEventUnion) -> int:
        from agent_core.models import serialize_event_persistent

        full = serialize_event_persistent(event)
        assert_event_type_registered(str(full["event_type"]))
        row = event_row_from_serialized(full)
        self._seq += 1
        db_row = {
            "store_seq": self._seq,
            "tenant_id": store_tenant_id(),
            "event_id": UUID(str(row["event_id"])),
            "run_id": UUID(str(row["run_id"])),
            "stage_id": UUID(str(row["stage_id"])) if row.get("stage_id") else None,
            "task_id": UUID(str(row["task_id"])) if row.get("task_id") else None,
            "event_type": str(row["event_type"]),
            "event_version": int(row["event_version"]),
            "occurred_at": datetime.fromisoformat(
                str(row["occurred_at"]).replace("Z", "+00:00"),
            ),
            "actor_role": row.get("actor_role"),
            "model_id": row.get("model_id"),
            "correlation_id": UUID(str(row["correlation_id"]))
            if row.get("correlation_id")
            else None,
            "causation_id": UUID(str(row["causation_id"])) if row.get("causation_id") else None,
            "payload": _json_safe(row["payload"]),
            "metadata": _json_safe(row.get("metadata") or {}),
        }
        self._rows.append(db_row)
        return self._seq

    def list_run_events(self, run_id: str) -> list[dict[str, Any]]:
        rid = UUID(run_id)
        out = [deepcopy(r) for r in self._scoped_rows() if r["run_id"] == rid]
        out.sort(key=lambda r: r["store_seq"])
        return out

    def list_all_event_rows(self) -> list[dict[str, Any]]:
        """All append-only rows (for in-memory memory index rebuild)."""
        out = deepcopy(self._scoped_rows())
        out.sort(key=lambda r: int(r["store_seq"]))
        return out

    def list_run_events_many(self, run_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for run_id in run_ids:
            out[str(run_id)] = self.list_run_events(str(run_id))
        return out

    def get_run_head(self, run_id: str) -> dict[str, Any] | None:
        rows = self.list_run_events(run_id)
        return rows[-1] if rows else None

    def max_store_seq_for_run(self, run_id: str) -> int | None:
        rid = UUID(run_id)
        mx: int | None = None
        for r in self._scoped_rows():
            if r["run_id"] != rid:
                continue
            s = int(r["store_seq"])
            mx = s if mx is None else max(mx, s)
        return mx

    def find_run_id_for_run_created_correlation(self, correlation_id: UUID) -> UUID | None:
        for r in self._scoped_rows():
            if r["event_type"] == "run.created" and r.get("correlation_id") == correlation_id:
                rid = r["run_id"]
                return rid if isinstance(rid, UUID) else UUID(str(rid))
        return None

    def _workflow_profile_for_run(self, run_id: UUID) -> str | None:
        rows = [r for r in self._scoped_rows() if r["run_id"] == run_id]
        rows.sort(key=lambda r: int(r["store_seq"]))
        for r in rows:
            if r["event_type"] != "run.created":
                continue
            pl = r.get("payload") or {}
            wf = pl.get("workflow_profile")
            return str(wf) if wf is not None else None
        return None

    def _run_created_at(self, run_id: UUID) -> datetime | None:
        rows = [r for r in self._scoped_rows() if r["run_id"] == run_id]
        rows.sort(key=lambda r: int(r["store_seq"]))
        for r in rows:
            if r["event_type"] != "run.created":
                continue
            at = r.get("occurred_at")
            if isinstance(at, datetime):
                if at.tzinfo is None:
                    return at.replace(tzinfo=timezone.utc)
                return at.astimezone(timezone.utc)
        return None

    def _run_has_escalation(self, run_id: UUID) -> bool:
        for r in self._scoped_rows():
            if r["run_id"] == run_id and r["event_type"] == "run.escalated":
                return True
        return False

    def _replay_list_status(self, run_id: UUID) -> str:
        """Match ``hermes_orchestrator.read_models.build_run_summary`` status for non-empty runs."""
        rows = [r for r in self._scoped_rows() if r["run_id"] == run_id]
        rows.sort(key=lambda r: int(r["store_seq"]))
        if not rows:
            return "unknown"
        terminal: str | None = None
        for r in rows:
            et = str(r["event_type"])
            if et in ("run.failed", "run.completed"):
                terminal = et
        latest_et = str(rows[-1]["event_type"])
        if terminal:
            return "terminal"
        if any(str(r["event_type"]) == "run.started" for r in rows):
            return "running"
        if latest_et == "run.created":
            return "created"
        return "running"

    def _filtered_ordered_run_rows(
        self,
        *,
        workflow_profile: str | None,
        workflow_profile_prefix: str | None,
        created_after: datetime | None,
        created_before: datetime | None,
        has_escalation: bool | None,
        list_status: str | None,
        order: str,
    ) -> list[tuple[UUID, int]]:
        best: dict[UUID, int] = {}
        for r in self._scoped_rows():
            rid = r["run_id"]
            seq = int(r["store_seq"])
            prev = best.get(rid, -1)
            if seq > prev:
                best[rid] = seq
        newest_first = order != "oldest_first"
        if order not in ("newest_first", "oldest_first"):
            newest_first = True
        items = [(u, best[u]) for u in best.keys()]
        items.sort(key=lambda t: (t[1], t[0]), reverse=newest_first)
        if workflow_profile:
            want = workflow_profile.strip().lower()
            items = [
                t
                for t in items
                if (self._workflow_profile_for_run(t[0]) or "").strip().lower() == want
            ]
        elif workflow_profile_prefix and str(workflow_profile_prefix).strip():
            pfx = str(workflow_profile_prefix).strip().lower()
            items = [
                t
                for t in items
                if ((self._workflow_profile_for_run(t[0]) or "").strip().lower()).startswith(pfx)
            ]
        if created_after is not None:
            ca = (
                created_after.replace(tzinfo=timezone.utc)
                if created_after.tzinfo is None
                else created_after.astimezone(timezone.utc)
            )
            items = [
                t for t in items if (at := self._run_created_at(t[0])) is not None and at >= ca
            ]
        if created_before is not None:
            cb = (
                created_before.replace(tzinfo=timezone.utc)
                if created_before.tzinfo is None
                else created_before.astimezone(timezone.utc)
            )
            items = [
                t for t in items if (at := self._run_created_at(t[0])) is not None and at <= cb
            ]
        if has_escalation is not None:
            items = [t for t in items if self._run_has_escalation(t[0]) == has_escalation]
        if list_status is not None:
            items = [t for t in items if self._replay_list_status(t[0]) == list_status]
        return items

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
        return len(
            self._filtered_ordered_run_rows(
                workflow_profile=workflow_profile,
                workflow_profile_prefix=workflow_profile_prefix,
                created_after=created_after,
                created_before=created_before,
                has_escalation=has_escalation,
                list_status=list_status,
                order="newest_first",
            ),
        )

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
        ordered = self._filtered_ordered_run_rows(
            workflow_profile=workflow_profile,
            workflow_profile_prefix=workflow_profile_prefix,
            created_after=created_after,
            created_before=created_before,
            has_escalation=has_escalation,
            list_status=list_status,
            order=order,
        )
        off = max(offset, 0)
        return [t[0] for t in ordered[off : off + limit]]

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
        lim = max(1, min(int(limit), 200))
        rows = self._filtered_ordered_run_rows(
            workflow_profile=workflow_profile,
            workflow_profile_prefix=workflow_profile_prefix,
            created_after=created_after,
            created_before=created_before,
            has_escalation=has_escalation,
            list_status=list_status,
            order=order,
        )
        oldest = order == "oldest_first"
        if order not in ("newest_first", "oldest_first"):
            oldest = False
        if oldest:
            filtered = [
                t
                for t in rows
                if (t[1] > cursor_after_seq)
                or (t[1] == cursor_after_seq and t[0] > cursor_after_run_id)
            ]
        else:
            filtered = [
                t
                for t in rows
                if (t[1] < cursor_after_seq)
                or (t[1] == cursor_after_seq and t[0] < cursor_after_run_id)
            ]
        chunk = filtered[: lim + 1]
        has_more = len(chunk) > lim
        return chunk[:lim], has_more

    def replay_validate(self, *, context: dict[str, Any] | None = None) -> list[HermesEventUnion]:
        """Round-trip all events through Pydantic (parity with Postgres read path)."""
        events: list[HermesEventUnion] = []
        for r in self._scoped_rows():
            d = serialized_event_from_row(r)
            events.append(validate_event_dict(d, context=context))
        return events
