from __future__ import annotations

from typing import Any

from agent_core.models import EventType


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("payload")
    return dict(raw) if isinstance(raw, dict) else {}


def run_research_briefs_from_events(rows: list[dict[str, Any]]) -> dict[str, Any]:
    briefs: dict[str, dict[str, Any]] = {}
    for row in rows:
        et = str(row.get("event_type") or "")
        pl = _payload(row)
        if et == EventType.RESEARCH_BRIEF_EMITTED.value:
            aid = str(pl.get("artifact_id") or "").strip()
            if not aid:
                continue
            briefs[aid] = {
                "brief_id": aid,
                "artifact_id": aid,
                "brief_kind": pl.get("brief_kind"),
                "domain_tag": pl.get("domain_tag"),
                "summary": pl.get("summary"),
                "sources": pl.get("sources") if isinstance(pl.get("sources"), list) else [],
                "status": "pending",
                "store_seq": row.get("store_seq"),
                "event_id": str(row.get("event_id") or ""),
            }
        elif et in (
            EventType.RESEARCH_BRIEF_APPROVED.value,
            EventType.RESEARCH_BRIEF_REJECTED.value,
        ):
            aid = str(pl.get("artifact_id") or "").strip()
            if aid in briefs:
                briefs[aid]["status"] = (
                    "approved" if et == EventType.RESEARCH_BRIEF_APPROVED.value else "rejected"
                )
                briefs[aid]["review_notes"] = pl.get("notes") or ""
    ordered = sorted(
        briefs.values(),
        key=lambda b: int(b.get("store_seq") or 0),
    )
    return {"briefs": ordered, "count": len(ordered)}
