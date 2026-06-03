from __future__ import annotations

import streamlit as st

from nimbusware_client.http import HTTPError
from nimbusware_console.components.ui_errors import render_api_error
from nimbusware_console.services import runs as runs_svc

_TIMELINE_FOCUS_KEY = "hermes_timeline_focus_store_seq"


def set_timeline_focus_store_seq(store_seq: int) -> None:
    st.session_state[_TIMELINE_FOCUS_KEY] = int(store_seq)


def render_run_detail_theater(run_id: str) -> None:
    if not run_id.strip():
        return
    st.subheader("Run theater")
    if not st.button("Load theater", key="hermes_load_run_theater"):
        focus = st.session_state.get(_TIMELINE_FOCUS_KEY)
        if focus:
            st.caption(
                f"Timeline focus: store_seq {focus} — load timeline to highlight nearby rows."
            )
        return
    try:
        body = runs_svc.fetch_run_theater(run_id.strip())
    except HTTPError as exc:
        render_api_error(exc)
        return
    messages = body.get("messages") if isinstance(body.get("messages"), list) else []
    if not messages:
        st.caption("No theater messages yet.")
        return
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue
        actor = str(msg.get("actor_display") or "System")
        headline = str(msg.get("headline") or "")
        severity = str(msg.get("severity") or "info")
        store_seq = int(msg.get("store_seq") or 0)
        event_id = str(msg.get("event_id") or "")
        label = f"{actor} ({severity}): {headline} [seq {store_seq}]"
        with st.expander(label, expanded=False):
            st.caption(f"event_id: {event_id}")
            refs = msg.get("refs")
            if isinstance(refs, dict) and refs:
                st.json(refs)
            body_md = msg.get("body_md")
            if isinstance(body_md, str) and body_md.strip():
                st.markdown(body_md)
            if store_seq > 0 and st.button(
                "Jump to timeline",
                key=f"hermes_theater_jump_{store_seq}_{i}",
            ):
                set_timeline_focus_store_seq(store_seq)
                st.info(
                    f"Focused store_seq {store_seq}. Click **Load timeline** to highlight "
                    f"events within ±5 sequence numbers.",
                )
