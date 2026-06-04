from __future__ import annotations

import streamlit as st

from nimbusware_client.http import get_json


def render_stitch_outcomes_section() -> None:
    with st.expander("Stitch transplant outcomes", expanded=False):
        try:
            body = get_json("/platform/analytics/stitch-outcomes", timeout=30.0)
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Could not load stitch analytics: {exc}")
            return
        rate = body.get("pass_rate_pct")
        sample = body.get("sample_size") or 0
        runs = body.get("runs_with_stitch") or 0
        passed = body.get("transplant_pass") or 0
        failed = body.get("transplant_fail") or 0
        limit = body.get("limit_runs") or 0
        if rate is None:
            st.caption(f"No scored transplants yet ({runs} run(s) with stitch.applied scanned).")
        else:
            st.metric("Transplant pass rate", f"{rate}%", help=f"{passed} pass / {failed} fail")
        st.caption(
            f"Sample size {sample} · runs with stitch {runs} · scan limit {limit} recent stitch runs",
        )
