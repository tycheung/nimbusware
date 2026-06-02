from __future__ import annotations

import streamlit as st

from nimbusware_console.pages.run_detail._imports_common import datetime, st, timezone
from nimbusware_console.pages.run_detail._imports_display_a import (
    integrator_gate_compatibility_ranking_caption,
    integrator_gate_compatibility_ranking_table_rows,
    integrator_gate_from_timeline,
    integrator_gate_latest_bundle_id_caption,
    integrator_gate_latest_export_filename_slug,
    integrator_gate_latest_export_json,
    integrator_gate_latest_metrics_table_rows,
    integrator_gate_latest_operator_metrics,
    integrator_gate_latest_operator_metrics_caption,
    integrator_gate_latest_operator_metrics_export_json,
    integrator_gate_latest_operator_metrics_table_rows_csv,
    integrator_gate_latest_score_margin_caption,
    integrator_gate_latest_summary_rows_csv,
    integrator_gate_latest_tag_overlap_caption,
    integrator_gate_summary_rows,
)


def _render_integrator_gate_latest(run_id: str, data: dict) -> None:
    _ig = integrator_gate_from_timeline(data)
    _ig_rows = integrator_gate_summary_rows(_ig)
    with st.expander("Integrator gate (from timeline)", expanded=False):
        if not _ig_rows:
            st.caption(
                "No integrator_gate summary on this timeline (no integrator "
                "gate.decision.emitted yet, or gate disabled for this run)."
            )
        else:
            st.caption(
                "Latest bundle integrator gate.decision.emitted summary "
                "(same top-level integrator_gate as GET …/timeline)."
            )
            st.dataframe(_ig_rows, use_container_width=True)
            _ig_rank_cap = integrator_gate_compatibility_ranking_caption(_ig)
            if _ig_rank_cap:
                st.caption(_ig_rank_cap)
            _ig_rank_rows = integrator_gate_compatibility_ranking_table_rows(_ig)
            if _ig_rank_rows:
                st.dataframe(
                    _ig_rank_rows,
                    use_container_width=True,
                    hide_index=True,
                )
            _ig_bundle_cap = integrator_gate_latest_bundle_id_caption(_ig)
            if _ig_bundle_cap:
                st.caption(_ig_bundle_cap)
            _ig_margin_cap = integrator_gate_latest_score_margin_caption(_ig)
            if _ig_margin_cap:
                st.caption(_ig_margin_cap)
            _ig_tag_cap = integrator_gate_latest_tag_overlap_caption(_ig)
            if _ig_tag_cap:
                st.caption(_ig_tag_cap)
            _ig_latest_m = integrator_gate_latest_operator_metrics(_ig)
            _ig_latest_metrics_cap = integrator_gate_latest_operator_metrics_caption(
                _ig_latest_m,
            )
            if _ig_latest_metrics_cap:
                st.caption(_ig_latest_metrics_cap)
            _ig_latest_ts = datetime.now(timezone.utc).strftime(
                "%Y%m%dT%H%M%SZ",
            )
            _ig_latest_slug = integrator_gate_latest_export_filename_slug(
                run_id.strip(),
            )
            if _ig_latest_m.get("present"):
                _ig_latest_rows = integrator_gate_latest_metrics_table_rows(
                    _ig_latest_m,
                )
                st.caption(
                    "Operator drill-down on **latest** gate: tag overlap, "
                    "failure reason when set, numeric score vs min pass."
                )
                st.dataframe(
                    _ig_latest_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                if _ig_latest_rows:
                    _ig_latest_metrics_json = integrator_gate_latest_operator_metrics_export_json(
                        _ig_latest_m,
                    )
                    _ig_latest_metrics_csv = integrator_gate_latest_operator_metrics_table_rows_csv(
                        _ig_latest_rows,
                    )
                    (
                        _ig_latest_metrics_dl_json_col,
                        _ig_latest_metrics_dl_csv_col,
                    ) = st.columns(2)
                    with _ig_latest_metrics_dl_json_col:
                        st.download_button(
                            label=("Download integrator gate latest operator metrics JSON"),
                            data=_ig_latest_metrics_json.encode("utf-8"),
                            file_name=(
                                "hermes_integrator_gate_latest_operator_metrics_"
                                f"{_ig_latest_slug}_{_ig_latest_ts}.json"
                            ),
                            mime="application/json",
                            key=("hermes_dl_integrator_gate_latest_operator_metrics_json"),
                        )
                    with _ig_latest_metrics_dl_csv_col:
                        if _ig_latest_metrics_csv:
                            st.download_button(
                                label=("Download integrator gate latest operator metrics CSV"),
                                data=_ig_latest_metrics_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_integrator_gate_latest_operator_metrics_"
                                    f"{_ig_latest_slug}_{_ig_latest_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key=("hermes_dl_integrator_gate_latest_operator_metrics_csv"),
                            )
                with st.expander(
                    "Raw integrator_gate latest operator metrics JSON",
                    expanded=False,
                ):
                    st.json(_ig_latest_m)
            _ig_latest_csv = integrator_gate_latest_summary_rows_csv(_ig_rows)
            _ig_latest_json = integrator_gate_latest_export_json(_ig)
            _ig_latest_dl_col, _ig_latest_dl_json_col = st.columns(2)
            with _ig_latest_dl_col:
                st.download_button(
                    label="Download integrator gate latest CSV",
                    data=_ig_latest_csv.encode("utf-8"),
                    file_name=(
                        f"hermes_integrator_gate_latest_{_ig_latest_slug}_{_ig_latest_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_integrator_gate_latest_csv",
                )
            with _ig_latest_dl_json_col:
                st.download_button(
                    label="Download integrator gate latest JSON",
                    data=_ig_latest_json.encode("utf-8"),
                    file_name=(
                        f"hermes_integrator_gate_latest_{_ig_latest_slug}_{_ig_latest_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_integrator_gate_latest_json",
                )
            with st.expander("Raw integrator_gate JSON", expanded=False):
                st.json(_ig)
