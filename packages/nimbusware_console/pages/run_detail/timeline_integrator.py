"""Run detail — timeline integrator panel."""

from __future__ import annotations

from typing import Any

import streamlit as st

from nimbusware_console.pages.run_detail._imports import *  # noqa: F403


def render_run_detail_timeline_integrator(run_id: str, data: dict) -> None:
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
                    _ig_latest_metrics_json = (
                        integrator_gate_latest_operator_metrics_export_json(
                            _ig_latest_m,
                        )
                    )
                    _ig_latest_metrics_csv = (
                        integrator_gate_latest_operator_metrics_table_rows_csv(
                            _ig_latest_rows,
                        )
                    )
                    (
                        _ig_latest_metrics_dl_json_col,
                        _ig_latest_metrics_dl_csv_col,
                    ) = st.columns(2)
                    with _ig_latest_metrics_dl_json_col:
                        st.download_button(
                            label=(
                                "Download integrator gate latest "
                                "operator metrics JSON"
                            ),
                            data=_ig_latest_metrics_json.encode("utf-8"),
                            file_name=(
                                "hermes_integrator_gate_latest_operator_metrics_"
                                f"{_ig_latest_slug}_{_ig_latest_ts}.json"
                            ),
                            mime="application/json",
                            key=(
                                "hermes_dl_integrator_gate_latest_"
                                "operator_metrics_json"
                            ),
                        )
                    with _ig_latest_metrics_dl_csv_col:
                        if _ig_latest_metrics_csv:
                            st.download_button(
                                label=(
                                    "Download integrator gate latest "
                                    "operator metrics CSV"
                                ),
                                data=_ig_latest_metrics_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_integrator_gate_latest_operator_metrics_"
                                    f"{_ig_latest_slug}_{_ig_latest_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key=(
                                    "hermes_dl_integrator_gate_latest_"
                                    "operator_metrics_csv"
                                ),
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
                        "hermes_integrator_gate_latest_"
                        f"{_ig_latest_slug}_{_ig_latest_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_integrator_gate_latest_csv",
                )
            with _ig_latest_dl_json_col:
                st.download_button(
                    label="Download integrator gate latest JSON",
                    data=_ig_latest_json.encode("utf-8"),
                    file_name=(
                        "hermes_integrator_gate_latest_"
                        f"{_ig_latest_slug}_{_ig_latest_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_integrator_gate_latest_json",
                )
            with st.expander("Raw integrator_gate JSON", expanded=False):
                st.json(_ig)
    _ig_hist = integrator_gate_history_from_timeline(data)
    _ig_hist_rows = integrator_gate_history_table_rows(_ig_hist)
    with st.expander("Integrator gate history (from timeline)", expanded=False):
        if not _ig_hist_rows:
            st.caption(
                "No ``integrator_gate_history`` on this timeline (same condition as "
                "empty latest summary — no integrator gate decisions recorded)."
            )
        else:
            st.caption(
                "Chronological ``gate.decision.emitted`` rows with integrator metadata "
                "(bounded on the API; latest row matches **Integrator gate** summary)."
            )
            _ig_hist_count_cap = integrator_gate_history_entry_count_caption(_ig_hist)
            if _ig_hist_count_cap:
                st.caption(_ig_hist_count_cap)
            _ig_hist_fail_cap = integrator_gate_history_failure_reason_caption(
                _ig_hist,
            )
            if _ig_hist_fail_cap:
                st.caption(_ig_hist_fail_cap)
            st.dataframe(_ig_hist_rows, use_container_width=True)
            _ig_hist_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _ig_hist_slug = integrator_gate_history_export_filename_slug(
                run_id.strip(),
            )
            _ig_hist_csv = integrator_gate_history_table_rows_csv(_ig_hist_rows)
            _ig_hist_json = integrator_gate_history_export_json(_ig_hist)
            _ig_dl_col, _ig_dl_json_col = st.columns(2)
            with _ig_dl_col:
                st.download_button(
                    label="Download integrator gate history CSV",
                    data=_ig_hist_csv.encode("utf-8"),
                    file_name=(
                        f"hermes_integrator_gate_history_{_ig_hist_slug}_{_ig_hist_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_integrator_gate_history_csv",
                )
            with _ig_dl_json_col:
                st.download_button(
                    label="Download integrator gate history JSON",
                    data=_ig_hist_json.encode("utf-8"),
                    file_name=(
                        f"hermes_integrator_gate_history_{_ig_hist_slug}_{_ig_hist_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_integrator_gate_history_json",
                )
            _ig_hist_metrics = integrator_gate_history_operator_metrics(_ig_hist)
            _ig_hist_metrics_cap = integrator_gate_history_operator_metrics_caption(
                _ig_hist_metrics,
            )
            if _ig_hist_metrics_cap:
                st.caption(_ig_hist_metrics_cap)
            _ig_hist_verdict_cap = integrator_gate_history_verdict_tally_caption(
                _ig_hist_metrics,
            )
            if _ig_hist_verdict_cap:
                st.caption(_ig_hist_verdict_cap)
            _ig_hist_bundles_cap = integrator_gate_history_distinct_bundles_caption(
                _ig_hist_metrics,
            )
            if _ig_hist_bundles_cap:
                st.caption(_ig_hist_bundles_cap)
            _ig_hist_score_cap = integrator_gate_history_score_range_caption(
                _ig_hist_metrics,
            )
            if _ig_hist_score_cap:
                st.caption(_ig_hist_score_cap)
            _ig_hist_margin_cap = integrator_gate_history_latest_margin_caption(
                _ig_hist_metrics,
            )
            if _ig_hist_margin_cap:
                st.caption(_ig_hist_margin_cap)
            _ig_hist_metric_rows = integrator_gate_history_metrics_table_rows(
                _ig_hist_metrics,
            )
            st.caption(
                "Operator metrics over the **same** bounded history. "
                "**Latest score minus min pass** is "
                "``integrator_score - min_score_to_pass`` on the latest row only; "
                "verdict may still reflect other rules."
            )
            st.dataframe(
                _ig_hist_metric_rows,
                use_container_width=True,
                hide_index=True,
            )
            if _ig_hist_metric_rows:
                _ig_hist_metrics_json = (
                    integrator_gate_history_operator_metrics_export_json(
                        _ig_hist_metrics,
                    )
                )
                _ig_hist_metrics_csv = (
                    integrator_gate_history_operator_metrics_table_rows_csv(
                        _ig_hist_metric_rows,
                    )
                )
                _ig_hist_metrics_dl_json_col, _ig_hist_metrics_dl_csv_col = (
                    st.columns(2)
                )
                with _ig_hist_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download integrator gate history "
                            "operator metrics JSON"
                        ),
                        data=_ig_hist_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_integrator_gate_history_operator_metrics_"
                            f"{_ig_hist_slug}_{_ig_hist_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_integrator_gate_history_operator_metrics_json",
                    )
                with _ig_hist_metrics_dl_csv_col:
                    if _ig_hist_metrics_csv:
                        st.download_button(
                            label=(
                            "Download integrator gate history "
                            "operator metrics CSV"
                        ),
                            data=_ig_hist_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_integrator_gate_history_operator_metrics_"
                                f"{_ig_hist_slug}_{_ig_hist_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_integrator_gate_history_operator_metrics_csv",
                        )
            with st.expander(
                "Raw integrator_gate_history operator metrics JSON",
                expanded=False,
            ):
                st.json(_ig_hist_metrics)
            with st.expander("Raw integrator_gate_history JSON", expanded=False):
                st.json(_ig_hist)
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
