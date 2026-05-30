from __future__ import annotations

from typing import Any

import streamlit as st

from nimbusware_console.pages.run_detail._imports import *  # noqa: F403


def render_run_detail_timeline_escalation(run_id: str, data: dict) -> None:
    _sr_marker_hist = self_refinement_marker_history_from_timeline(data)
    _sr_marker_hist_rows = self_refinement_marker_history_table_rows(
        _sr_marker_hist,
    )
    with st.expander(
        "Self-refinement marker history (from timeline)",
        expanded=False,
    ):
        if not _sr_marker_hist_rows:
            st.caption(
                "No ``self_refinement_marker_history`` on this timeline "
                "(no self_refinement:policy stage.started markers yet)."
            )
        else:
            st.caption(
                "Chronological policy markers (bounded on the API; latest "
                "summary matches **Self-refinement** above)."
            )
            _sr_marker_hist_cap = (
                self_refinement_marker_history_entry_count_caption(
                    _sr_marker_hist,
                )
            )
            if _sr_marker_hist_cap:
                st.caption(_sr_marker_hist_cap)
            _sr_marker_hist_metrics = (
                self_refinement_marker_history_operator_metrics(
                    _sr_marker_hist,
                )
            )
            _sr_marker_hist_metrics_cap = (
                self_refinement_marker_history_operator_metrics_caption(
                    _sr_marker_hist_metrics,
                )
            )
            if _sr_marker_hist_metrics_cap:
                st.caption(_sr_marker_hist_metrics_cap)
            _sr_marker_hist_metric_rows = (
                self_refinement_marker_history_operator_metrics_table_rows(
                    _sr_marker_hist_metrics,
                )
            )
            _sr_marker_hist_ts = datetime.now(timezone.utc).strftime(
                "%Y%m%dT%H%M%SZ",
            )
            _sr_marker_hist_slug = (
                self_refinement_marker_history_export_filename_slug(
                    run_id.strip(),
                )
            )
            if _sr_marker_hist_metric_rows:
                st.dataframe(
                    _sr_marker_hist_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _sr_marker_hist_metrics_json = (
                    self_refinement_marker_history_operator_metrics_export_json(
                        _sr_marker_hist_metrics,
                    )
                )
                _sr_marker_hist_metrics_csv = (
                    self_refinement_marker_history_operator_metrics_table_rows_csv(
                        _sr_marker_hist_metric_rows,
                    )
                )
                (
                    _sr_marker_hist_metrics_dl_json_col,
                    _sr_marker_hist_metrics_dl_csv_col,
                ) = st.columns(2)
                with _sr_marker_hist_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download self-refinement marker history "
                            "operator metrics JSON"
                        ),
                        data=_sr_marker_hist_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_self_refinement_marker_history_operator_metrics_"
                            f"{_sr_marker_hist_slug}_{_sr_marker_hist_ts}.json"
                        ),
                        mime="application/json",
                        key=(
                            "hermes_dl_self_refinement_marker_history_"
                            "operator_metrics_json"
                        ),
                    )
                with _sr_marker_hist_metrics_dl_csv_col:
                    if _sr_marker_hist_metrics_csv:
                        st.download_button(
                            label=(
                                "Download self-refinement marker history "
                                "operator metrics CSV"
                            ),
                            data=_sr_marker_hist_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_self_refinement_marker_history_operator_metrics_"
                                f"{_sr_marker_hist_slug}_{_sr_marker_hist_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key=(
                                "hermes_dl_self_refinement_marker_history_"
                                "operator_metrics_csv"
                            ),
                        )
            st.dataframe(_sr_marker_hist_rows, use_container_width=True)
            _sr_marker_hist_csv = self_refinement_marker_history_table_rows_csv(
                _sr_marker_hist_rows,
            )
            _sr_marker_hist_json = self_refinement_marker_history_export_json(
                _sr_marker_hist,
            )
            _sr_marker_dl_col, _sr_marker_dl_json_col = st.columns(2)
            with _sr_marker_dl_col:
                st.download_button(
                    label="Download marker history CSV",
                    data=_sr_marker_hist_csv.encode("utf-8"),
                    file_name=(
                        "hermes_self_refinement_marker_history_"
                        f"{_sr_marker_hist_slug}_{_sr_marker_hist_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_self_refinement_marker_history_csv",
                )
            with _sr_marker_dl_json_col:
                st.download_button(
                    label="Download marker history JSON",
                    data=_sr_marker_hist_json.encode("utf-8"),
                    file_name=(
                        "hermes_self_refinement_marker_history_"
                        f"{_sr_marker_hist_slug}_{_sr_marker_hist_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_self_refinement_marker_history_json",
                )
            with st.expander(
                "Raw self_refinement_marker_history JSON",
                expanded=False,
            ):
                st.json(_sr_marker_hist)
    _re = run_escalated_from_timeline(data)
    _re_rows = run_escalated_summary_rows(_re)
    with st.expander("Run escalated (from timeline)", expanded=False):
        if not _re_rows:
            st.caption(
                "No run_escalated summary on this timeline (no run.escalated "
                "events yet)."
            )
        else:
            st.caption(
                "Latest run.escalated summary (same top-level run_escalated as "
                "GET …/timeline)."
            )
            st.dataframe(_re_rows, use_container_width=True)
            _re_reason_cap = run_escalated_reason_summary_caption(_re)
            if _re_reason_cap:
                st.caption(_re_reason_cap)
            _re_at_cap = run_escalated_occurred_at_caption(_re)
            if _re_at_cap:
                st.caption(_re_at_cap)
            _re_event_cap = run_escalated_event_id_caption(_re)
            if _re_event_cap:
                st.caption(_re_event_cap)
            _re_notes_cap = run_escalated_notes_preview_caption(_re)
            if _re_notes_cap:
                st.caption(_re_notes_cap)
            _re_root = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
            _re_cap = run_escalated_policy_cross_ref_caption(_re_root, _re)
            if _re_cap:
                st.caption(_re_cap)
            _re_actor_notes = run_escalated_actor_without_notes_caption(_re)
            if _re_actor_notes:
                st.caption(_re_actor_notes)
            _re_metrics = run_escalated_operator_metrics(_re)
            _re_metrics_cap = run_escalated_operator_metrics_caption(
                _re_metrics,
            )
            if _re_metrics_cap:
                st.caption(_re_metrics_cap)
            _re_metric_rows = run_escalated_operator_metrics_table_rows(
                _re_metrics,
            )
            _re_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _re_slug = run_escalated_export_filename_slug(run_id.strip())
            if _re_metric_rows:
                st.dataframe(
                    _re_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _re_metrics_json = run_escalated_operator_metrics_export_json(
                    _re_metrics,
                )
                _re_metrics_csv = (
                    run_escalated_operator_metrics_table_rows_csv(
                        _re_metric_rows,
                    )
                )
                _re_metrics_dl_json_col, _re_metrics_dl_csv_col = st.columns(2)
                with _re_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download run escalated operator "
                            "metrics JSON"
                        ),
                        data=_re_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_run_escalated_operator_metrics_"
                            f"{_re_slug}_{_re_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_run_escalated_operator_metrics_json",
                    )
                with _re_metrics_dl_csv_col:
                    if _re_metrics_csv:
                        st.download_button(
                            label=(
                                "Download run escalated operator "
                                "metrics CSV"
                            ),
                            data=_re_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_run_escalated_operator_metrics_"
                                f"{_re_slug}_{_re_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_run_escalated_operator_metrics_csv",
                        )
            _re_sum_csv = run_escalated_summary_rows_csv(_re_rows)
            _re_sum_json = run_escalated_export_json(_re)
            _re_sum_dl_col, _re_sum_dl_json_col = st.columns(2)
            with _re_sum_dl_col:
                if _re_sum_csv:
                    st.download_button(
                        label="Download run escalated summary CSV",
                        data=_re_sum_csv.encode("utf-8"),
                        file_name=(
                            "hermes_run_escalated_summary_"
                            f"{_re_slug}_{_re_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_run_escalated_summary_csv",
                    )
            with _re_sum_dl_json_col:
                st.download_button(
                    label="Download run escalated summary JSON",
                    data=_re_sum_json.encode("utf-8"),
                    file_name=(
                        "hermes_run_escalated_summary_"
                        f"{_re_slug}_{_re_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_run_escalated_summary_json",
                )
            with st.expander("Raw run_escalated JSON", expanded=False):
                st.json(_re)
    _re_hist = run_escalated_history_from_timeline(data)
    _re_hist_rows = run_escalated_history_table_rows(_re_hist)
    with st.expander("Run escalated history (from timeline)", expanded=False):
        if not _re_hist_rows:
            st.caption(
                "No ``run_escalated_history`` on this timeline (no "
                "run.escalated events recorded)."
            )
        else:
            st.caption(
                "Chronological ``run.escalated`` rows (bounded on the API; "
                "latest row matches **Run escalated** summary)."
            )
            _re_hist_count_cap = run_escalated_history_entry_count_caption(
                _re_hist,
            )
            if _re_hist_count_cap:
                st.caption(_re_hist_count_cap)
            _re_hist_metrics = run_escalated_history_operator_metrics(_re_hist)
            _re_hist_metrics_cap = run_escalated_history_operator_metrics_caption(
                _re_hist_metrics,
            )
            if _re_hist_metrics_cap:
                st.caption(_re_hist_metrics_cap)
            _re_hist_actors_cap = run_escalated_history_distinct_actors_caption(
                _re_hist_metrics,
            )
            if _re_hist_actors_cap:
                st.caption(_re_hist_actors_cap)
            _re_hist_metric_rows = run_escalated_history_operator_metrics_table_rows(
                _re_hist_metrics,
            )
            _re_hist_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _re_hist_slug = run_escalated_history_export_filename_slug(
                run_id.strip(),
            )
            if _re_hist_metric_rows:
                st.dataframe(
                    _re_hist_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _re_hist_metrics_json = (
                    run_escalated_history_operator_metrics_export_json(
                        _re_hist_metrics,
                    )
                )
                _re_hist_metrics_csv = (
                    run_escalated_history_operator_metrics_table_rows_csv(
                        _re_hist_metric_rows,
                    )
                )
                (
                    _re_hist_metrics_dl_json_col,
                    _re_hist_metrics_dl_csv_col,
                ) = st.columns(2)
                with _re_hist_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download run escalated history operator "
                            "metrics JSON"
                        ),
                        data=_re_hist_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_run_escalated_history_operator_metrics_"
                            f"{_re_hist_slug}_{_re_hist_ts}.json"
                        ),
                        mime="application/json",
                        key=(
                            "hermes_dl_run_escalated_history_operator_"
                            "metrics_json"
                        ),
                    )
                with _re_hist_metrics_dl_csv_col:
                    if _re_hist_metrics_csv:
                        st.download_button(
                            label=(
                                "Download run escalated history operator "
                                "metrics CSV"
                            ),
                            data=_re_hist_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_run_escalated_history_operator_metrics_"
                                f"{_re_hist_slug}_{_re_hist_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key=(
                                "hermes_dl_run_escalated_history_operator_"
                                "metrics_csv"
                            ),
                        )
            st.dataframe(_re_hist_rows, use_container_width=True)
            _re_hist_csv = run_escalated_history_table_rows_csv(_re_hist_rows)
            _re_hist_json = run_escalated_history_export_json(_re_hist)
            _re_hist_dl_col, _re_hist_dl_json_col = st.columns(2)
            with _re_hist_dl_col:
                st.download_button(
                    label="Download run escalated history CSV",
                    data=_re_hist_csv.encode("utf-8"),
                    file_name=(
                        "hermes_run_escalated_history_"
                        f"{_re_hist_slug}_{_re_hist_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_run_escalated_history_csv",
                )
            with _re_hist_dl_json_col:
                st.download_button(
                    label="Download run escalated history JSON",
                    data=_re_hist_json.encode("utf-8"),
                    file_name=(
                        "hermes_run_escalated_history_"
                        f"{_re_hist_slug}_{_re_hist_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_run_escalated_history_json",
                )
            with st.expander("Raw run_escalated_history JSON", expanded=False):
                st.json(_re_hist)
    _re_delta = run_escalated_delta_from_timeline(data)
    with st.expander("Run escalated delta (latest vs prior)", expanded=False):
        if not _re_delta:
            st.caption(
                "No ``run_escalated_delta`` — need at least two "
                "run.escalated events on this timeline."
            )
        else:
            st.caption(
                "Diff between the last two ``run.escalated`` events "
                "(same field as GET …/timeline ``run_escalated_delta``)."
            )
            _re_delta_cap = run_escalated_delta_transition_caption(_re_delta)
            if _re_delta_cap:
                st.caption(_re_delta_cap)
            _re_delta_metrics = run_escalated_delta_operator_metrics(_re_delta)
            _re_delta_metrics_cap = run_escalated_delta_operator_metrics_caption(
                _re_delta_metrics,
            )
            if _re_delta_metrics_cap:
                st.caption(_re_delta_metrics_cap)
            _re_delta_metric_rows = run_escalated_delta_operator_metrics_table_rows(
                _re_delta_metrics,
            )
            _re_delta_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _re_delta_slug = run_escalated_delta_export_filename_slug(
                run_id.strip(),
            )
            if _re_delta_metric_rows:
                st.dataframe(
                    _re_delta_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _re_delta_metrics_json = (
                    run_escalated_delta_operator_metrics_export_json(
                        _re_delta_metrics,
                    )
                )
                _re_delta_metrics_csv = (
                    run_escalated_delta_operator_metrics_table_rows_csv(
                        _re_delta_metric_rows,
                    )
                )
                (
                    _re_delta_metrics_dl_json_col,
                    _re_delta_metrics_dl_csv_col,
                ) = st.columns(2)
                with _re_delta_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download run escalated delta operator "
                            "metrics JSON"
                        ),
                        data=_re_delta_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_run_escalated_delta_operator_metrics_"
                            f"{_re_delta_slug}_{_re_delta_ts}.json"
                        ),
                        mime="application/json",
                        key=(
                            "hermes_dl_run_escalated_delta_operator_"
                            "metrics_json"
                        ),
                    )
                with _re_delta_metrics_dl_csv_col:
                    if _re_delta_metrics_csv:
                        st.download_button(
                            label=(
                                "Download run escalated delta operator "
                                "metrics CSV"
                            ),
                            data=_re_delta_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_run_escalated_delta_operator_metrics_"
                                f"{_re_delta_slug}_{_re_delta_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key=(
                                "hermes_dl_run_escalated_delta_operator_"
                                "metrics_csv"
                            ),
                        )
            _re_delta_sum_rows = run_escalated_delta_summary_rows(_re_delta)
            _re_delta_csv = run_escalated_delta_table_rows_csv(_re_delta_sum_rows)
            _re_delta_json = run_escalated_delta_export_json(_re_delta)
            _re_delta_dl_col, _re_delta_dl_json_col = st.columns(2)
            with _re_delta_dl_col:
                st.download_button(
                    label="Download run escalated delta CSV",
                    data=_re_delta_csv.encode("utf-8"),
                    file_name=(
                        "hermes_run_escalated_delta_"
                        f"{_re_delta_slug}_{_re_delta_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_run_escalated_delta_csv",
                )
            with _re_delta_dl_json_col:
                st.download_button(
                    label="Download run escalated delta JSON",
                    data=_re_delta_json.encode("utf-8"),
                    file_name=(
                        "hermes_run_escalated_delta_"
                        f"{_re_delta_slug}_{_re_delta_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_run_escalated_delta_json",
                )
            with st.expander("Raw run_escalated_delta JSON", expanded=False):
                st.json(_re_delta)
