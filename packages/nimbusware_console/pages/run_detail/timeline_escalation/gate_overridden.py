from __future__ import annotations

import streamlit as st


def _render_gate_overridden(run_id: str, data: dict) -> None:
    summary = data.get("gate_overridden")
    history = data.get("gate_overridden_history") or []
    with st.expander("Gate overridden (from timeline)", expanded=False):
        if not summary and not history:
            st.caption(
                "No gate_overridden summary on this timeline (no gate.overridden events yet)."
            )
        else:
            if summary:
                st.caption("Latest gate.overridden (audit trail; does not auto-unblock gates).")
                st.json(summary)
            if history:
                st.dataframe(history, use_container_width=True)
