from __future__ import annotations

import streamlit as st


def _research_brief_rows(events: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for ev in events:
        if ev.get("event_type") != "research.brief.emitted":
            continue
        payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
        rows.append(
            {
                "brief_kind": payload.get("brief_kind"),
                "domain_tag": payload.get("domain_tag"),
                "summary": (payload.get("summary") or "")[:120],
            },
        )
    return rows


def _stitch_rows(events: list[dict]) -> list[dict]:
    want = {
        "stitch.license.checked",
        "stitch.dependency.checked",
        "stitch.plan.emitted",
        "stitch.applied",
    }
    return [
        {
            "event_type": ev.get("event_type"),
            "occurred_at": ev.get("occurred_at"),
        }
        for ev in events
        if ev.get("event_type") in want
    ]


def render_run_detail_research_stitch(run_id: str, data: dict) -> None:
    events = data.get("events") if isinstance(data.get("events"), list) else []
    briefs = _research_brief_rows(events)
    stitch = _stitch_rows(events)
    with st.expander("Research timeline", expanded=False):
        if not briefs:
            st.caption("No research.brief.emitted events on this run.")
        else:
            st.dataframe(briefs, use_container_width=True)
    with st.expander("Transplant preview (stitch audit)", expanded=False):
        if not stitch:
            st.caption("No stitch license/dependency/plan/apply events yet.")
        else:
            st.dataframe(stitch, use_container_width=True)
