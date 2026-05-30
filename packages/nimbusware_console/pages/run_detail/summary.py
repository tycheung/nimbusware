from __future__ import annotations

from typing import Any

import httpx
import streamlit as st

from nimbusware_client.http import get_json

from nimbusware_console.pages.run_detail._imports import *  # noqa: F403


def render_run_detail_summary(run_id: str) -> None:
    if st.button("Load run summary") and run_id.strip():
        try:
            data = get_json(f"/runs/{run_id.strip()}", timeout=30.0)
            st.subheader("Summary")
            c1m, c2m, c3m = st.columns(3)
            c1m.metric("Events", data.get("event_count", "—"))
            c2m.metric("Findings", data.get("findings_count", "—"))
            c3m.metric("Escalated", "yes" if data.get("has_escalation") else "no")
            _sum_metrics = run_detail_summary_operator_metrics(data)
            _sum_metrics_cap = run_detail_summary_operator_metrics_caption(_sum_metrics)
            if _sum_metrics_cap:
                st.caption(_sum_metrics_cap)
            _sum_metric_rows = run_detail_summary_operator_metrics_table_rows(
                _sum_metrics,
            )
            if _sum_metric_rows:
                st.dataframe(
                    _sum_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
            _mem_policy = memory_policy_from_run_summary(data)
            if _mem_policy:
                with st.expander("Memory policy (from run.created)", expanded=False):
                    _mem_rows = memory_policy_table_rows(_mem_policy)
                    if _mem_rows:
                        st.dataframe(_mem_rows, use_container_width=True, hide_index=True)
            _sum_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _sum_metrics_slug = run_detail_summary_operator_metrics_export_filename_slug()
            _sum_metrics_json = run_detail_summary_operator_metrics_export_json(
                _sum_metrics,
            )
            _sum_metrics_csv = run_detail_summary_operator_metrics_table_rows_csv(
                _sum_metric_rows,
            )
            _sum_m_dl_json_col, _sum_m_dl_csv_col = st.columns(2)
            with _sum_m_dl_json_col:
                st.download_button(
                    label="Download run summary operator metrics JSON",
                    data=_sum_metrics_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_sum_metrics_slug}_"
                        f"{run_detail_summary_export_filename_slug(run_id.strip())}_"
                        f"{_sum_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_run_summary_metrics_json",
                )
            with _sum_m_dl_csv_col:
                if _sum_metrics_csv:
                    st.download_button(
                        label="Download run summary operator metrics CSV",
                        data=_sum_metrics_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_sum_metrics_slug}_"
                            f"{run_detail_summary_export_filename_slug(run_id.strip())}_"
                            f"{_sum_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_run_summary_metrics_csv",
                    )
            _sum_slug = run_detail_summary_export_filename_slug(run_id.strip())
            _sum_json = run_detail_summary_export_json(data)
            st.download_button(
                label="Download run summary JSON",
                data=_sum_json.encode("utf-8"),
                file_name=f"hermes_run_summary_{_sum_slug}_{_sum_ts}.json",
                mime="application/json",
                key="hermes_dl_run_summary_json",
            )
            with st.expander("Raw summary JSON", expanded=False):
                st.json(data)
        except httpx.HTTPError as exc:
            st.error(f"API error: {exc}")
