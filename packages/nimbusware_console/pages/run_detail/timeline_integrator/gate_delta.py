from __future__ import annotations

import streamlit as st

from nimbusware_console.pages.run_detail._imports_common import datetime, st, timezone
from nimbusware_console.pages.run_detail._imports_display_a import (
    integrator_gate_delta_bundle_changed_caption,
    integrator_gate_delta_export_filename_slug,
    integrator_gate_delta_export_json,
    integrator_gate_delta_from_timeline,
    integrator_gate_delta_operator_metrics,
    integrator_gate_delta_operator_metrics_caption,
    integrator_gate_delta_operator_metrics_export_json,
    integrator_gate_delta_operator_metrics_table_rows_csv,
    integrator_gate_delta_operator_table_rows,
    integrator_gate_delta_summary_rows,
    integrator_gate_delta_summary_rows_csv,
    integrator_gate_delta_transition_caption,
    integrator_gate_delta_verdict_changed_caption,
)


def _render_integrator_gate_delta(run_id: str, data: dict) -> None:
    _ig_delta = integrator_gate_delta_from_timeline(data)
    _ig_delta_rows = integrator_gate_delta_summary_rows(_ig_delta)
    with st.expander("Integrator gate delta (latest vs prior)", expanded=False):
        if not _ig_delta_rows:
            st.caption(
                "No ``integrator_gate_delta`` — need at least two integrator "
                "gate decisions on this timeline."
            )
        else:
            st.caption(
                "Diff between the last two ``gate.decision.emitted`` integrator rows "
                "(same field as GET …/timeline ``integrator_gate_delta``)."
            )
            _ig_delta_cap = integrator_gate_delta_transition_caption(_ig_delta)
            if _ig_delta_cap:
                st.caption(_ig_delta_cap)
            _ig_delta_verdict_cap = integrator_gate_delta_verdict_changed_caption(
                _ig_delta,
            )
            if _ig_delta_verdict_cap:
                st.caption(_ig_delta_verdict_cap)
            _ig_delta_bundle_cap = integrator_gate_delta_bundle_changed_caption(
                _ig_delta,
            )
            if _ig_delta_bundle_cap:
                st.caption(_ig_delta_bundle_cap)
            st.dataframe(_ig_delta_rows, use_container_width=True)
            _ig_delta_ts = datetime.now(timezone.utc).strftime(
                "%Y%m%dT%H%M%SZ",
            )
            _ig_delta_slug = integrator_gate_delta_export_filename_slug(
                run_id.strip(),
            )
            _ig_d_m = integrator_gate_delta_operator_metrics(_ig_delta)
            _ig_d_metrics_cap = integrator_gate_delta_operator_metrics_caption(
                _ig_d_m,
            )
            if _ig_d_metrics_cap:
                st.caption(_ig_d_metrics_cap)
            if _ig_d_m.get("present"):
                _ig_d_op_rows = integrator_gate_delta_operator_table_rows(_ig_d_m)
                st.caption(
                    "Operator hints on **delta**: score direction, verdict transition, "
                    "bundle id change."
                )
                st.dataframe(
                    _ig_d_op_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                if _ig_d_op_rows:
                    _ig_d_metrics_json = (
                        integrator_gate_delta_operator_metrics_export_json(
                            _ig_d_m,
                        )
                    )
                    _ig_d_metrics_csv = (
                        integrator_gate_delta_operator_metrics_table_rows_csv(
                            _ig_d_op_rows,
                        )
                    )
                    _ig_d_metrics_dl_json_col, _ig_d_metrics_dl_csv_col = (
                        st.columns(2)
                    )
                    with _ig_d_metrics_dl_json_col:
                        st.download_button(
                            label=(
                                "Download integrator gate delta "
                                "operator metrics JSON"
                            ),
                            data=_ig_d_metrics_json.encode("utf-8"),
                            file_name=(
                                "hermes_integrator_gate_delta_operator_metrics_"
                                f"{_ig_delta_slug}_{_ig_delta_ts}.json"
                            ),
                            mime="application/json",
                            key=(
                                "hermes_dl_integrator_gate_delta_"
                                "operator_metrics_json"
                            ),
                        )
                    with _ig_d_metrics_dl_csv_col:
                        if _ig_d_metrics_csv:
                            st.download_button(
                                label=(
                                    "Download integrator gate delta "
                                    "operator metrics CSV"
                                ),
                                data=_ig_d_metrics_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_integrator_gate_delta_operator_metrics_"
                                    f"{_ig_delta_slug}_{_ig_delta_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key=(
                                    "hermes_dl_integrator_gate_delta_"
                                    "operator_metrics_csv"
                                ),
                            )
                with st.expander(
                    "Raw integrator_gate_delta operator metrics JSON",
                    expanded=False,
                ):
                    st.json(_ig_d_m)
            _ig_delta_csv = integrator_gate_delta_summary_rows_csv(_ig_delta_rows)
            _ig_delta_json = integrator_gate_delta_export_json(_ig_delta)
            _ig_delta_dl_col, _ig_delta_dl_json_col = st.columns(2)
            with _ig_delta_dl_col:
                st.download_button(
                    label="Download integrator gate delta CSV",
                    data=_ig_delta_csv.encode("utf-8"),
                    file_name=(
                        "hermes_integrator_gate_delta_"
                        f"{_ig_delta_slug}_{_ig_delta_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_integrator_gate_delta_csv",
                )
            with _ig_delta_dl_json_col:
                st.download_button(
                    label="Download integrator gate delta JSON",
                    data=_ig_delta_json.encode("utf-8"),
                    file_name=(
                        "hermes_integrator_gate_delta_"
                        f"{_ig_delta_slug}_{_ig_delta_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_integrator_gate_delta_json",
                )
            with st.expander("Raw integrator_gate_delta JSON", expanded=False):
                st.json(_ig_delta)
