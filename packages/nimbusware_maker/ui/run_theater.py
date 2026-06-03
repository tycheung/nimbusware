from __future__ import annotations

import streamlit as st

from nimbusware_maker.services import theater as theater_svc


def render_run_theater_panel() -> None:
    st.subheader("Run theater")
    run_id = st.text_input(
        "Run ID",
        value=st.session_state.get("maker_active_run_id", ""),
        key="maker_theater_run_id",
    )
    if not run_id.strip():
        st.info("Select an active run to follow the narrative thread.")
        return
    rid = run_id.strip()
    st.session_state["maker_active_run_id"] = rid
    try:
        body = theater_svc.fetch_run_theater(rid)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Theater: {exc}")
        return
    messages = body.get("messages") if isinstance(body.get("messages"), list) else []
    if not messages:
        st.caption("No theater messages yet — events will appear as the run progresses.")
        return
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        actor = str(msg.get("actor_display") or "System")
        headline = str(msg.get("headline") or "")
        severity = str(msg.get("severity") or "info")
        st.chat_message("assistant" if actor == "System" else "user").markdown(
            f"**{actor}** ({severity}): {headline}",
        )
        body_md = msg.get("body_md")
        if isinstance(body_md, str) and body_md.strip():
            st.caption(body_md[:1200])
