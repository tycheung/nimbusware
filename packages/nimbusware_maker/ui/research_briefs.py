from __future__ import annotations

import streamlit as st

from nimbusware_maker.services import research as research_svc


def render_research_briefs_panel(run_id: str) -> None:
    st.markdown("**Research briefs**")
    try:
        body = research_svc.fetch_run_research(run_id)
    except Exception as exc:  # noqa: BLE001
        st.caption(f"Research: {exc}")
        return
    briefs = body.get("briefs") if isinstance(body.get("briefs"), list) else []
    if not briefs:
        st.caption("No research briefs on this run yet.")
        return
    for brief in briefs:
        if not isinstance(brief, dict):
            continue
        bid = str(brief.get("brief_id") or "")
        status = str(brief.get("status") or "pending")
        kind = str(brief.get("brief_kind") or "")
        with st.expander(f"{kind} — {bid} ({status})", expanded=status == "pending"):
            st.write(str(brief.get("summary") or "")[:2000])
            if status == "pending":
                notes = st.text_input("Notes", key=f"rb_notes_{bid}", value="")
                cols = st.columns(2)
                with cols[0]:
                    if st.button("Approve", key=f"rb_ok_{bid}"):
                        try:
                            research_svc.approve_research_brief(run_id, bid, notes=notes)
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(str(exc))
                with cols[1]:
                    if st.button("Reject", key=f"rb_no_{bid}"):
                        try:
                            research_svc.reject_research_brief(run_id, bid, notes=notes)
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(str(exc))
