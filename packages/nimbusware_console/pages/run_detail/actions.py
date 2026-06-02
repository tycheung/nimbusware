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
            ov_actor = st.text_input("Override actor_id", value="human:operator", key="ov_actor")
            ov_reason = st.text_input("Override reason_code", value="manual_gate_override")
            ov_stage = st.text_input("Override stage_name", value="slice.gate")
            ov_policy = st.text_input("Override policy_snapshot_id (optional)", value="")
            if st.button("Record gate override (gate.overridden)"):
                try:
                    body = {
                        "actor_id": ov_actor,
                        "reason_code": ov_reason,
                        "stage_name": ov_stage,
                    }
                    if ov_policy.strip():
                        body["policy_snapshot_id"] = ov_policy.strip()
                    st.success(runs_svc.post_override_gate(run_id, body))
                except HTTPError as exc:
                    render_api_error(exc)
