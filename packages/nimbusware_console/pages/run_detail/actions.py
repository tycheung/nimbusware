from __future__ import annotations

import httpx
import streamlit as st

from nimbusware_client.http import get_json, post_json


def render_run_detail_actions(run_id: str) -> None:
    st.divider()
    with st.container(border=True):
        st.subheader("Actions (POST /v1/runs/…/actions/…)")
        if run_id.strip():
            if st.button("Record retry (stage.started retry)"):
                try:
                    st.success(post_json(f"/runs/{run_id.strip()}/actions/retry", {}, timeout=30.0))
                except httpx.HTTPError as exc:
                    st.error(f"API error: {exc}")
            esc_actor = st.text_input("Escalate actor_id", value="human:operator")
            esc_reason = st.text_input("Escalate reason_code", value="manual_review")
            esc_notes = st.text_area("Escalate notes (optional)", value="")
            if st.button("Record escalation (run.escalated)"):
                try:
                    body = {"actor_id": esc_actor, "reason_code": esc_reason}
                    if esc_notes.strip():
                        body["notes"] = esc_notes.strip()
                    st.success(
                        post_json(
                            f"/runs/{run_id.strip()}/actions/escalate",
                            body,
                            timeout=30.0,
                        ),
                    )
                except httpx.HTTPError as exc:
                    st.error(f"API error: {exc}")
