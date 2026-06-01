from __future__ import annotations

import streamlit as st

from nimbusware_client.http import HTTPError
from nimbusware_console.components.ui_errors import render_api_error
from nimbusware_console.services import runs as runs_svc


def render_run_detail_actions(run_id: str) -> None:
    st.divider()
    with st.container(border=True):
        st.subheader("Actions (POST /v1/runs/…/actions/…)")
        if run_id.strip():
            if st.button("Record retry (stage.started retry)"):
                try:
                    st.success(runs_svc.post_retry(run_id))
                except HTTPError as exc:
                    render_api_error(exc)
            esc_actor = st.text_input("Escalate actor_id", value="human:operator")
            esc_reason = st.text_input("Escalate reason_code", value="manual_review")
            esc_notes = st.text_area("Escalate notes (optional)", value="")
            if st.button("Record escalation (run.escalated)"):
                try:
                    body = {"actor_id": esc_actor, "reason_code": esc_reason}
                    if esc_notes.strip():
                        body["notes"] = esc_notes.strip()
                    st.success(runs_svc.post_escalate(run_id, body))
                except HTTPError as exc:
                    render_api_error(exc)
