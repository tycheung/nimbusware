from __future__ import annotations

from typing import Any

import streamlit as st

from nimbusware_client.http import HTTPError
from nimbusware_console.components.ui_errors import render_api_error
from nimbusware_console.pages.run_detail._imports_common import datetime, json, st, timezone
from nimbusware_console.pages.run_detail._imports_display_b import (
    timeline_events_export_filename_slug,
    timeline_events_export_json,
    timeline_events_from_body,
    timeline_events_operator_metrics,
    timeline_events_operator_metrics_caption,
    timeline_events_operator_metrics_export_json,
    timeline_events_operator_metrics_table_rows,
    timeline_events_operator_metrics_table_rows_csv,
    timeline_events_table_rows,
    timeline_events_table_rows_csv,
)
from nimbusware_console.run_list_pagination_display.timeline_events import (
    timeline_events_near_store_seq,
)
from nimbusware_console.services import runs as runs_svc

_TIMELINE_FOCUS_KEY = "hermes_timeline_focus_store_seq"


def render_run_detail_timeline_core(run_id: str) -> tuple[dict[str, Any], list] | None:
    if st.button("Load timeline") and run_id.strip():
        try:
            data = runs_svc.fetch_timeline(run_id)
        except HTTPError as exc:
            render_api_error(exc)
            return None
        events = timeline_events_from_body(data)
        focus_seq = st.session_state.get(_TIMELINE_FOCUS_KEY)
        if isinstance(focus_seq, int) and focus_seq > 0:
            st.caption(f"Highlighting events near store_seq {focus_seq} (±5).")
            events_display = timeline_events_near_store_seq(events, focus_seq)
            if not events_display:
                st.warning("No timeline events matched focus; showing full timeline.")
                events_display = events
        else:
            events_display = events
        st.subheader("Timeline")
        _tl_metrics = timeline_events_operator_metrics(events)
        _tl_metrics_cap = timeline_events_operator_metrics_caption(_tl_metrics)
        if _tl_metrics_cap:
            st.caption(_tl_metrics_cap)
        _tl_metric_rows = timeline_events_operator_metrics_table_rows(
            _tl_metrics,
        )
        _tl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _tl_slug = timeline_events_export_filename_slug(run_id.strip())
        if _tl_metric_rows:
            st.dataframe(
                _tl_metric_rows,
                use_container_width=True,
                hide_index=True,
            )
            _tl_metrics_json = timeline_events_operator_metrics_export_json(
                _tl_metrics,
            )
            _tl_metrics_csv = timeline_events_operator_metrics_table_rows_csv(
                _tl_metric_rows,
            )
            _tl_metrics_dl_json_col, _tl_metrics_dl_csv_col = st.columns(2)
            with _tl_metrics_dl_json_col:
                st.download_button(
                    label="Download timeline events operator metrics JSON",
                    data=_tl_metrics_json.encode("utf-8"),
                    file_name=(f"hermes_timeline_events_operator_metrics_{_tl_slug}_{_tl_ts}.json"),
                    mime="application/json",
                    key="hermes_dl_timeline_events_operator_metrics_json",
                )
            with _tl_metrics_dl_csv_col:
                if _tl_metrics_csv:
                    st.download_button(
                        label="Download timeline events operator metrics CSV",
                        data=_tl_metrics_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_timeline_events_operator_metrics_{_tl_slug}_{_tl_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_timeline_events_operator_metrics_csv",
                    )
        _tl_events_json = timeline_events_export_json(data)
        _tl_events_rows = timeline_events_table_rows(events_display)
        _tl_events_csv = timeline_events_table_rows_csv(_tl_events_rows)
        st.download_button(
            label="Download timeline JSON",
            data=json.dumps(data, indent=2).encode("utf-8"),
            file_name=f"{run_id.strip()}_timeline.json",
            mime="application/json",
        )
        _tl_dl_json_col, _tl_dl_csv_col = st.columns(2)
        with _tl_dl_json_col:
            st.download_button(
                label="Download timeline events JSON (subset)",
                data=_tl_events_json.encode("utf-8"),
                file_name=(f"hermes_timeline_events_{_tl_slug}_{_tl_ts}.json"),
                mime="application/json",
                key="hermes_dl_timeline_events_json",
            )
        with _tl_dl_csv_col:
            if _tl_events_csv:
                st.download_button(
                    label="Download timeline events CSV",
                    data=_tl_events_csv.encode("utf-8"),
                    file_name=(f"hermes_timeline_events_{_tl_slug}_{_tl_ts}.csv"),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_timeline_events_csv",
                )
        with st.expander("Raw timeline events JSON", expanded=False):
            st.json(events_display)
        return data, events
    return None
