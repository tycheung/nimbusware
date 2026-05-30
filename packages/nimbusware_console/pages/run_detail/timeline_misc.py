"""Run detail — timeline misc panel."""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from nimbusware_console.pages.run_detail._imports import *  # noqa: F403


def render_run_detail_timeline_misc(run_id: str, data: dict) -> None:
    _wf_pick = data.get("workflow_profile") if isinstance(data, dict) else None
    if not isinstance(_wf_pick, str) or not _wf_pick.strip():
        _wf_pick = os.environ.get("HERMES_WORKFLOW_PROFILE", "nimbusware_production")
    with st.expander("Phase 3 critic stages (from timeline)", expanded=False):
        st.caption(phase3_critique_caption(data))
        _p3_rows = phase3_critique_table_rows(data)
        if _p3_rows:
            st.dataframe(_p3_rows, use_container_width=True)
    _ms_tl = data.get("micro_slice") if isinstance(data, dict) else None
    if isinstance(_ms_tl, dict) and _ms_tl:
        with st.expander("Micro-slice summary (from timeline)", expanded=False):
            st.json(_ms_tl)
        _pkt = latest_slice_context_packet_from_timeline(data)
        if _pkt:
            with st.expander("Slice context packet (latest)", expanded=False):
                st.json(_pkt)
    _mem_ret = memory_retrieval_timeline_summary(data.get("events") or [])
    _mem_idx = memory_indexed_timeline_summary(data.get("events") or [])
    if _mem_ret or _mem_idx:
        with st.expander("Memory retrieval / index (from timeline)", expanded=False):
            if _mem_ret:
                st.caption("Last retrieval event summary")
                st.json(_mem_ret)
            if _mem_idx:
                st.caption("Last memory.indexed summary")
                st.json(_mem_idx)
    _ss = security_scan_on_verify_from_timeline(data)
    _ss_rows = security_scan_on_verify_summary_rows(_ss)
    _ssm_align_payload = security_scan_metadata_workflow_explainer_payload(
        _iroot,
        workflow_profile=_wf_pick,
    )
    _ss_align_cap = security_scan_metadata_timeline_workflow_alignment_caption(
        timeline_security_scan_on_verify=_ss,
        explainer_payload=_ssm_align_payload,
    )
    with st.expander("Security scan on verify (from timeline)", expanded=False):
        if _ss_align_cap:
            st.caption(_ss_align_cap)
        if not _ss_rows:
            st.caption(
                "No security_scan_on_verify summary on this timeline (no "
                "finding.created with security_scan_* metadata yet)."
            )
        else:
            st.caption(
                "Latest finding.created with verifier security scan metadata "
                "(same top-level security_scan_on_verify as GET …/timeline)."
            )
            st.dataframe(_ss_rows, use_container_width=True)
            _ss_snip_len = security_scan_snippet_length_caption(_ss)
            if _ss_snip_len:
                st.caption(_ss_snip_len)
            _ss_snip_lines = security_scan_snippet_line_count_caption(_ss)
            if _ss_snip_lines:
                st.caption(_ss_snip_lines)
            _ss_ids_cap = security_scan_finding_event_ids_caption(_ss)
            if _ss_ids_cap:
                st.caption(_ss_ids_cap)
            _ss_occ_age = security_scan_occurred_at_age_caption(_ss)
            if _ss_occ_age:
                st.caption(_ss_occ_age)
            _ss_cat_sev = security_scan_category_severity_caption(_ss)
            if _ss_cat_sev:
                st.caption(_ss_cat_sev)
            _ss_finding_metrics = (
                security_scan_on_verify_latest_operator_metrics(_ss)
            )
            _ss_finding_metrics_cap = (
                security_scan_on_verify_latest_operator_metrics_caption(
                    _ss_finding_metrics,
                )
            )
            if _ss_finding_metrics_cap:
                st.caption(_ss_finding_metrics_cap)
            _ss_finding_metric_rows = (
                security_scan_on_verify_latest_operator_metrics_table_rows(
                    _ss_finding_metrics,
                )
            )
            _ss_latest_ts = datetime.now(timezone.utc).strftime(
                "%Y%m%dT%H%M%SZ",
            )
            _ss_latest_slug = security_scan_on_verify_latest_export_filename_slug(
                run_id.strip(),
            )
            if _ss_finding_metric_rows:
                st.dataframe(
                    _ss_finding_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _ss_finding_metrics_json = (
                    security_scan_on_verify_latest_operator_metrics_export_json(
                        _ss_finding_metrics,
                    )
                )
                _ss_finding_metrics_csv = (
                    security_scan_on_verify_latest_operator_metrics_table_rows_csv(
                        _ss_finding_metric_rows,
                    )
                )
                (
                    _ss_finding_metrics_dl_json_col,
                    _ss_finding_metrics_dl_csv_col,
                ) = st.columns(2)
                with _ss_finding_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download security scan finding operator "
                            "metrics JSON"
                        ),
                        data=_ss_finding_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_security_scan_finding_operator_metrics_"
                            f"{_ss_latest_slug}_{_ss_latest_ts}.json"
                        ),
                        mime="application/json",
                        key=(
                            "hermes_dl_security_scan_finding_operator_"
                            "metrics_json"
                        ),
                    )
                with _ss_finding_metrics_dl_csv_col:
                    if _ss_finding_metrics_csv:
                        st.download_button(
                            label=(
                                "Download security scan finding operator "
                                "metrics CSV"
                            ),
                            data=_ss_finding_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_security_scan_finding_operator_metrics_"
                                f"{_ss_latest_slug}_{_ss_latest_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key=(
                                "hermes_dl_security_scan_finding_operator_"
                                "metrics_csv"
                            ),
                        )
            _ss_lint = security_scan_linter_nonzero_caption(_ss)
            if _ss_lint:
                st.caption(_ss_lint)
            _ss_linter_rows = security_scan_linter_status_rows(_ss)
            if _ss_linter_rows:
                st.caption("Per-linter status (Ruff / Bandit)")
                st.dataframe(
                    _ss_linter_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _ss_linter_summary = (
                    security_scan_linter_status_summary_caption(_ss)
                )
                if _ss_linter_summary:
                    st.caption(_ss_linter_summary)
                _ss_worst = security_scan_linter_worst_status_caption(_ss)
                if _ss_worst:
                    st.caption(_ss_worst)
                _ss_exits = security_scan_linter_exit_codes_caption(_ss)
                if _ss_exits:
                    st.caption(_ss_exits)
                _ss_failed = security_scan_linter_failed_linters_caption(_ss)
                if _ss_failed:
                    st.caption(_ss_failed)
                _ss_ok = security_scan_linter_ok_linters_caption(_ss)
                if _ss_ok:
                    st.caption(_ss_ok)
                _ss_missing = security_scan_linter_missing_linters_caption(_ss)
                if _ss_missing:
                    st.caption(_ss_missing)
                _ss_latest_ts = datetime.now(timezone.utc).strftime(
                    "%Y%m%dT%H%M%SZ",
                )
                _ss_latest_slug = (
                    security_scan_on_verify_latest_export_filename_slug(
                        run_id.strip(),
                    )
                )
                _ss_linter_metrics = security_scan_linter_operator_metrics(_ss)
                _ss_linter_metrics_cap = security_scan_linter_operator_metrics_caption(
                    _ss_linter_metrics,
                )
                if _ss_linter_metrics_cap:
                    st.caption(_ss_linter_metrics_cap)
                _ss_linter_metric_rows = (
                    security_scan_linter_operator_metrics_table_rows(
                        _ss_linter_metrics,
                    )
                )
                if _ss_linter_metric_rows:
                    st.dataframe(
                        _ss_linter_metric_rows,
                        use_container_width=True,
                        hide_index=True,
                    )
                    _ss_linter_metrics_json = (
                        security_scan_linter_operator_metrics_export_json(
                            _ss_linter_metrics,
                        )
                    )
                    _ss_linter_metrics_csv = (
                        security_scan_linter_operator_metrics_table_rows_csv(
                            _ss_linter_metric_rows,
                        )
                    )
                    _ss_linter_metrics_dl_json_col, _ss_linter_metrics_dl_csv_col = (
                        st.columns(2)
                    )
                    with _ss_linter_metrics_dl_json_col:
                        st.download_button(
                            label=(
                                "Download security scan linter "
                                "operator metrics JSON"
                            ),
                            data=_ss_linter_metrics_json.encode("utf-8"),
                            file_name=(
                                "hermes_security_scan_linter_operator_metrics_"
                                f"{_ss_latest_slug}_{_ss_latest_ts}.json"
                            ),
                            mime="application/json",
                            key=(
                                "hermes_dl_security_scan_linter_"
                                "operator_metrics_json"
                            ),
                        )
                    with _ss_linter_metrics_dl_csv_col:
                        if _ss_linter_metrics_csv:
                            st.download_button(
                                label=(
                                    "Download security scan linter "
                                    "operator metrics CSV"
                                ),
                                data=_ss_linter_metrics_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_security_scan_linter_operator_metrics_"
                                    f"{_ss_latest_slug}_{_ss_latest_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key=(
                                    "hermes_dl_security_scan_linter_"
                                    "operator_metrics_csv"
                                ),
                            )
                with st.expander(
                    "Raw linter operator metrics JSON",
                    expanded=False,
                ):
                    st.json(_ss_linter_metrics)
            _ss_latest_csv = security_scan_on_verify_latest_summary_rows_csv(
                _ss_rows,
            )
            _ss_latest_json = security_scan_on_verify_latest_export_json(_ss)
            _ss_latest_dl_col, _ss_latest_dl_json_col = st.columns(2)
            with _ss_latest_dl_col:
                st.download_button(
                    label="Download security scan on verify latest CSV",
                    data=_ss_latest_csv.encode("utf-8"),
                    file_name=(
                        "hermes_security_scan_on_verify_latest_"
                        f"{_ss_latest_slug}_{_ss_latest_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_security_scan_on_verify_latest_csv",
                )
            with _ss_latest_dl_json_col:
                st.download_button(
                    label="Download security scan on verify latest JSON",
                    data=_ss_latest_json.encode("utf-8"),
                    file_name=(
                        "hermes_security_scan_on_verify_latest_"
                        f"{_ss_latest_slug}_{_ss_latest_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_security_scan_on_verify_latest_json",
                )
            with st.expander("Raw security_scan_on_verify JSON", expanded=False):
                st.json(_ss)
    _ss_hist = security_scan_history_from_timeline(data)
    _ss_hist_rows = security_scan_history_table_rows(_ss_hist)
    with st.expander(
        "Security scan history (from timeline)",
        expanded=False,
    ):
        if not _ss_hist_rows:
            st.caption(
                "No ``security_scan_on_verify_history`` on this timeline "
                "(no finding.created with security_scan_* metadata yet)."
            )
        else:
            st.caption(
                "Chronological verifier scan findings (bounded on the API; "
                "latest row matches **Security scan on verify** summary)."
            )
            _ss_hist_cap = security_scan_history_entry_count_caption(_ss_hist)
            if _ss_hist_cap:
                st.caption(_ss_hist_cap)
            _ss_hist_metrics = security_scan_history_operator_metrics(_ss_hist)
            _ss_hist_metrics_cap = security_scan_history_operator_metrics_caption(
                _ss_hist_metrics,
            )
            if _ss_hist_metrics_cap:
                st.caption(_ss_hist_metrics_cap)
            _ss_hist_sev_cap = security_scan_history_severity_sample_caption(
                _ss_hist,
            )
            if _ss_hist_sev_cap:
                st.caption(_ss_hist_sev_cap)
            _ss_hist_metric_rows = security_scan_history_operator_metrics_table_rows(
                _ss_hist_metrics,
            )
            _ss_hist_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _ss_hist_slug = security_scan_history_export_filename_slug(
                run_id.strip(),
            )
            if _ss_hist_metric_rows:
                st.dataframe(
                    _ss_hist_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _ss_hist_metrics_json = (
                    security_scan_history_operator_metrics_export_json(
                        _ss_hist_metrics,
                    )
                )
                _ss_hist_metrics_csv = (
                    security_scan_history_operator_metrics_table_rows_csv(
                        _ss_hist_metric_rows,
                    )
                )
                (
                    _ss_hist_metrics_dl_json_col,
                    _ss_hist_metrics_dl_csv_col,
                ) = st.columns(2)
                with _ss_hist_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download security scan history operator "
                            "metrics JSON"
                        ),
                        data=_ss_hist_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_security_scan_history_operator_metrics_"
                            f"{_ss_hist_slug}_{_ss_hist_ts}.json"
                        ),
                        mime="application/json",
                        key=(
                            "hermes_dl_security_scan_history_operator_"
                            "metrics_json"
                        ),
                    )
                with _ss_hist_metrics_dl_csv_col:
                    if _ss_hist_metrics_csv:
                        st.download_button(
                            label=(
                                "Download security scan history operator "
                                "metrics CSV"
                            ),
                            data=_ss_hist_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_security_scan_history_operator_metrics_"
                                f"{_ss_hist_slug}_{_ss_hist_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key=(
                                "hermes_dl_security_scan_history_operator_"
                                "metrics_csv"
                            ),
                        )
            st.dataframe(_ss_hist_rows, use_container_width=True)
            _ss_hist_csv = security_scan_history_table_rows_csv(_ss_hist_rows)
            _ss_hist_json = security_scan_history_export_json(_ss_hist)
            _ss_hist_dl_col, _ss_hist_dl_json_col = st.columns(2)
            with _ss_hist_dl_col:
                st.download_button(
                    label="Download security scan history CSV",
                    data=_ss_hist_csv.encode("utf-8"),
                    file_name=(
                        f"hermes_security_scan_history_{_ss_hist_slug}_{_ss_hist_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_security_scan_history_csv",
                )
            with _ss_hist_dl_json_col:
                st.download_button(
                    label="Download security scan history JSON",
                    data=_ss_hist_json.encode("utf-8"),
                    file_name=(
                        f"hermes_security_scan_history_{_ss_hist_slug}_{_ss_hist_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_security_scan_history_json",
                )
            with st.expander(
                "Raw security_scan_on_verify_history JSON",
                expanded=False,
            ):
                st.json(_ss_hist)
    _uc_tl = universal_critique_from_timeline(data)
    _uc_tl_rows = universal_critique_timeline_stage_rows(_uc_tl)
    with st.expander("Universal critique (from timeline)", expanded=False):
        if not _uc_tl_rows:
            st.caption(
                "No universal_critique summary on this timeline (no "
                "``*.critique`` gate.decision.emitted events yet)."
            )
        else:
            st.caption(
                "Latest gate decision per critique stage (same top-level "
                "universal_critique as GET …/timeline)."
            )
            _uc_tl_fail_cap = universal_critique_timeline_fail_count_caption(
                _uc_tl,
            )
            if _uc_tl_fail_cap:
                st.caption(_uc_tl_fail_cap)
            _uc_tl_metrics = universal_critique_timeline_operator_metrics(_uc_tl)
            _uc_tl_metrics_cap = (
                universal_critique_timeline_operator_metrics_caption(
                    _uc_tl_metrics,
                )
            )
            if _uc_tl_metrics_cap:
                st.caption(_uc_tl_metrics_cap)
            _uc_tl_metric_rows = (
                universal_critique_timeline_operator_metrics_table_rows(
                    _uc_tl_metrics,
                )
            )
            _uc_tl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _uc_tl_slug = universal_critique_timeline_export_filename_slug(
                run_id.strip(),
            )
            if _uc_tl_metric_rows:
                st.dataframe(
                    _uc_tl_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _uc_tl_metrics_json = (
                    universal_critique_timeline_operator_metrics_export_json(
                        _uc_tl_metrics,
                    )
                )
                _uc_tl_metrics_csv = (
                    universal_critique_timeline_operator_metrics_table_rows_csv(
                        _uc_tl_metric_rows,
                    )
                )
                (
                    _uc_tl_metrics_dl_json_col,
                    _uc_tl_metrics_dl_csv_col,
                ) = st.columns(2)
                with _uc_tl_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download universal critique operator "
                            "metrics JSON"
                        ),
                        data=_uc_tl_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_universal_critique_operator_metrics_"
                            f"{_uc_tl_slug}_{_uc_tl_ts}.json"
                        ),
                        mime="application/json",
                        key=(
                            "hermes_dl_universal_critique_operator_"
                            "metrics_json"
                        ),
                    )
                with _uc_tl_metrics_dl_csv_col:
                    if _uc_tl_metrics_csv:
                        st.download_button(
                            label=(
                                "Download universal critique operator "
                                "metrics CSV"
                            ),
                            data=_uc_tl_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_universal_critique_operator_metrics_"
                                f"{_uc_tl_slug}_{_uc_tl_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key=(
                                "hermes_dl_universal_critique_operator_"
                                "metrics_csv"
                            ),
                        )
            st.dataframe(_uc_tl_rows, use_container_width=True)
            _uc_tl_fail_rows = universal_critique_timeline_fail_stage_rows(_uc_tl)
            _uc_tl_fail_cap_stages = universal_critique_timeline_fail_stage_caption(
                _uc_tl,
            )
            if _uc_tl_fail_cap_stages:
                st.caption(_uc_tl_fail_cap_stages)
            if _uc_tl_fail_rows:
                st.caption("FAIL stages only (subset of table above)")
                st.dataframe(
                    _uc_tl_fail_rows,
                    use_container_width=True,
                    hide_index=True,
                )
            _uc_tl_json = universal_critique_timeline_export_json(_uc_tl)
            _uc_stages_csv = universal_critique_timeline_stage_rows_csv(
                _uc_tl_rows,
            )
            if _uc_tl_fail_rows:
                _uc_fail_csv = universal_critique_fail_stage_rows_csv(_uc_tl_fail_rows)
                (
                    _uc_dl_stages_col,
                    _uc_dl_csv_col,
                    _uc_dl_json_col,
                ) = st.columns(3)
                with _uc_dl_stages_col:
                    st.download_button(
                        label="Download universal critique all stages CSV",
                        data=_uc_stages_csv.encode("utf-8"),
                        file_name=(
                            "hermes_universal_critique_stages_"
                            f"{_uc_tl_slug}_{_uc_tl_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_universal_critique_stages_csv",
                    )
                with _uc_dl_csv_col:
                    st.download_button(
                        label="Download universal critique FAIL stages CSV",
                        data=_uc_fail_csv.encode("utf-8"),
                        file_name=(
                            "hermes_universal_critique_fail_stages_"
                            f"{_uc_tl_slug}_{_uc_tl_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_universal_critique_fail_csv",
                    )
                with _uc_dl_json_col:
                    st.download_button(
                        label="Download universal critique timeline JSON",
                        data=_uc_tl_json.encode("utf-8"),
                        file_name=(
                            "hermes_universal_critique_timeline_"
                            f"{_uc_tl_slug}_{_uc_tl_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_universal_critique_timeline_json",
                    )
            else:
                _uc_dl_stages_col, _uc_dl_json_col = st.columns(2)
                with _uc_dl_stages_col:
                    st.download_button(
                        label="Download universal critique all stages CSV",
                        data=_uc_stages_csv.encode("utf-8"),
                        file_name=(
                            "hermes_universal_critique_stages_"
                            f"{_uc_tl_slug}_{_uc_tl_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_universal_critique_stages_csv",
                    )
                with _uc_dl_json_col:
                    st.download_button(
                        label="Download universal critique timeline JSON",
                        data=_uc_tl_json.encode("utf-8"),
                        file_name=(
                            "hermes_universal_critique_timeline_"
                            f"{_uc_tl_slug}_{_uc_tl_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_universal_critique_timeline_json",
                    )
            with st.expander("Raw universal_critique JSON", expanded=False):
                st.json(_uc_tl)
    _sf = scraper_fetch_from_timeline(data)
    _sf_rows = scraper_fetch_summary_rows(_sf)
    with st.expander("Scraper fetch (from timeline)", expanded=False):
        if not _sf_rows:
            st.caption(
                "No scraper_fetch summary on this timeline (no terminal "
                "scraper:fetch stage.passed / stage.failed yet)."
            )
        else:
            st.caption(
                "Latest scraper:fetch terminal stage summary (same top-level "
                "scraper_fetch as GET …/timeline)."
            )
            _sf_outcome_cap = scraper_fetch_outcome_caption(_sf)
            if _sf_outcome_cap:
                st.caption(_sf_outcome_cap)
            _sf_fail_cap = scraper_fetch_failure_reason_caption(_sf)
            if _sf_fail_cap:
                st.caption(_sf_fail_cap)
            _sf_metrics = scraper_fetch_operator_metrics(_sf)
            _sf_metrics_cap = scraper_fetch_operator_metrics_caption(_sf_metrics)
            if _sf_metrics_cap:
                st.caption(_sf_metrics_cap)
            _sf_metric_rows = scraper_fetch_operator_metrics_table_rows(
                _sf_metrics,
            )
            _sf_sum_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _sf_sum_slug = scraper_fetch_summary_export_filename_slug(
                run_id.strip(),
            )
            if _sf_metric_rows:
                st.dataframe(
                    _sf_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _sf_metrics_json = scraper_fetch_operator_metrics_export_json(
                    _sf_metrics,
                )
                _sf_metrics_csv = scraper_fetch_operator_metrics_table_rows_csv(
                    _sf_metric_rows,
                )
                _sf_metrics_dl_json_col, _sf_metrics_dl_csv_col = st.columns(2)
                with _sf_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download scraper fetch operator "
                            "metrics JSON"
                        ),
                        data=_sf_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_scraper_fetch_operator_metrics_"
                            f"{_sf_sum_slug}_{_sf_sum_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_scraper_fetch_operator_metrics_json",
                    )
                with _sf_metrics_dl_csv_col:
                    if _sf_metrics_csv:
                        st.download_button(
                            label=(
                                "Download scraper fetch operator "
                                "metrics CSV"
                            ),
                            data=_sf_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_scraper_fetch_operator_metrics_"
                                f"{_sf_sum_slug}_{_sf_sum_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_scraper_fetch_operator_metrics_csv",
                        )
            st.dataframe(_sf_rows, use_container_width=True)
            _sf_fetch_rows = scraper_fetch_fetches_table_rows(_sf)
            if _sf_fetch_rows:
                st.caption("Per-URL fetches (from timeline ``scraper_fetch.fetches``)")
                _sf_artifacts_cap = scraper_fetch_artifacts_caption(_sf)
                if _sf_artifacts_cap:
                    st.caption(_sf_artifacts_cap)
                st.dataframe(_sf_fetch_rows, use_container_width=True)
                _sf_fetch_ts = datetime.now(timezone.utc).strftime(
                    "%Y%m%dT%H%M%SZ",
                )
                _sf_fetch_slug = scraper_fetch_fetches_export_filename_slug(
                    run_id.strip(),
                )
                _sf_fetch_csv = scraper_fetch_fetches_table_rows_csv(
                    _sf_fetch_rows,
                )
                _sf_fetch_json = scraper_fetch_fetches_export_json(_sf)
                _sf_fetch_dl_col, _sf_fetch_dl_json_col = st.columns(2)
                with _sf_fetch_dl_col:
                    st.download_button(
                        label="Download scraper fetches CSV",
                        data=_sf_fetch_csv.encode("utf-8"),
                        file_name=(
                            "hermes_scraper_fetch_fetches_"
                            f"{_sf_fetch_slug}_{_sf_fetch_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_scraper_fetch_fetches_csv",
                    )
                with _sf_fetch_dl_json_col:
                    st.download_button(
                        label="Download scraper fetches JSON",
                        data=_sf_fetch_json.encode("utf-8"),
                        file_name=(
                            "hermes_scraper_fetch_fetches_"
                            f"{_sf_fetch_slug}_{_sf_fetch_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_scraper_fetch_fetches_json",
                    )
            _sf_sum_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _sf_sum_slug = scraper_fetch_summary_export_filename_slug(
                run_id.strip(),
            )
            _sf_sum_csv = scraper_fetch_summary_rows_csv(_sf_rows)
            _sf_sum_json = scraper_fetch_summary_export_json(_sf)
            _sf_sum_dl_col, _sf_sum_dl_json_col = st.columns(2)
            with _sf_sum_dl_col:
                st.download_button(
                    label="Download scraper fetch summary CSV",
                    data=_sf_sum_csv.encode("utf-8"),
                    file_name=(
                        "hermes_scraper_fetch_summary_"
                        f"{_sf_sum_slug}_{_sf_sum_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_scraper_fetch_summary_csv",
                )
            with _sf_sum_dl_json_col:
                st.download_button(
                    label="Download scraper fetch summary JSON",
                    data=_sf_sum_json.encode("utf-8"),
                    file_name=(
                        "hermes_scraper_fetch_summary_"
                        f"{_sf_sum_slug}_{_sf_sum_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_scraper_fetch_summary_json",
                )
            with st.expander("Raw scraper_fetch JSON", expanded=False):
                st.json(_sf)
    _pf = preflight_history_from_timeline(data)
    _pf_rows = preflight_history_summary_rows(_pf)
    with st.expander("Preflight history (from timeline)", expanded=False):
        if not _pf_rows:
            st.caption(
                "No preflight summary on this timeline (no "
                "model.preflight.passed yet, or skipped via "
                "HERMES_SKIP_PREFLIGHT)."
            )
        else:
            st.caption(
                "Latest model.preflight.passed summary (same top-level "
                "preflight as GET …/timeline). Histogram bucket edges: "
                "50 / 100 / 250 / 500 / 1000 / 2500 / 5000 / 10000 ms."
            )
            _pf_metrics = preflight_history_operator_metrics(_pf)
            _pf_metrics_cap = preflight_history_operator_metrics_caption(
                _pf_metrics,
            )
            if _pf_metrics_cap:
                st.caption(_pf_metrics_cap)
            _pf_metric_rows = preflight_history_operator_metrics_table_rows(
                _pf_metrics,
            )
            _pf_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _pf_slug = preflight_history_export_filename_slug(run_id.strip())
            if _pf_metric_rows:
                st.dataframe(
                    _pf_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _pf_metrics_json = preflight_history_operator_metrics_export_json(
                    _pf_metrics,
                )
                _pf_metrics_csv = preflight_history_operator_metrics_table_rows_csv(
                    _pf_metric_rows,
                )
                _pf_metrics_dl_json_col, _pf_metrics_dl_csv_col = st.columns(2)
                with _pf_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download preflight history operator "
                            "metrics JSON"
                        ),
                        data=_pf_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_preflight_history_operator_metrics_"
                            f"{_pf_slug}_{_pf_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_preflight_history_operator_metrics_json",
                    )
                with _pf_metrics_dl_csv_col:
                    if _pf_metrics_csv:
                        st.download_button(
                            label=(
                                "Download preflight history operator "
                                "metrics CSV"
                            ),
                            data=_pf_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_preflight_history_operator_metrics_"
                                f"{_pf_slug}_{_pf_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_preflight_history_operator_metrics_csv",
                        )
            st.dataframe(_pf_rows, use_container_width=True)
            _pf_hist_mode_cap = preflight_history_histogram_mode_caption(_pf)
            if _pf_hist_mode_cap:
                st.caption(_pf_hist_mode_cap)
            _pf_samples_cap = preflight_history_samples_table_caption(_pf)
            if _pf_samples_cap:
                st.caption(_pf_samples_cap)
            _pf_sample_rows = preflight_history_latency_samples_table_rows(
                _pf,
            )
            if _pf_sample_rows:
                st.dataframe(_pf_sample_rows, use_container_width=True)
            _pf_p95_src_cap = preflight_history_p95_source_caption(_pf)
            if _pf_p95_src_cap:
                st.caption(_pf_p95_src_cap)
            _pf_p95_ms_cap = preflight_history_p95_latency_caption(_pf)
            if _pf_p95_ms_cap:
                st.caption(_pf_p95_ms_cap)
            _pf_event_cap = preflight_history_event_id_caption(_pf)
            if _pf_event_cap:
                st.caption(_pf_event_cap)
            _pf_checks_cap = preflight_history_checks_passed_caption(_pf)
            if _pf_checks_cap:
                st.caption(_pf_checks_cap)
            _pf_vm_cap = preflight_history_validated_model_caption(_pf)
            if _pf_vm_cap:
                st.caption(_pf_vm_cap)
            _pf_provider_cap = preflight_history_provider_caption(_pf)
            if _pf_provider_cap:
                st.caption(_pf_provider_cap)
            _pf_sc_cap = preflight_history_sample_count_caption(_pf)
            if _pf_sc_cap:
                st.caption(_pf_sc_cap)
            _pf_ctx_cap = preflight_history_context_tokens_caption(_pf)
            if _pf_ctx_cap:
                st.caption(_pf_ctx_cap)
            _hist = preflight_history_histogram_payload(_pf)
            if _hist and _hist.get("count"):
                _bars = [
                    {
                        "bucket": (
                            f"<={b['le_ms']}ms"
                            if b["le_ms"] is not None
                            else ">10000ms"
                        ),
                        "count": b["count"],
                    }
                    for b in _hist["buckets"]
                ]
                st.bar_chart(
                    _bars,
                    x="bucket",
                    y="count",
                    use_container_width=True,
                )
            _pf_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _pf_slug = preflight_history_export_filename_slug(run_id.strip())
            _pf_csv = preflight_history_summary_rows_csv(_pf_rows)
            _pf_json = preflight_history_export_json(_pf)
            _pf_dl_col, _pf_dl_json_col = st.columns(2)
            with _pf_dl_col:
                st.download_button(
                    label="Download preflight timeline CSV",
                    data=_pf_csv.encode("utf-8"),
                    file_name=(
                        "hermes_preflight_timeline_"
                        f"{_pf_slug}_{_pf_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_preflight_timeline_csv",
                )
            with _pf_dl_json_col:
                st.download_button(
                    label="Download preflight timeline JSON",
                    data=_pf_json.encode("utf-8"),
                    file_name=(
                        "hermes_preflight_timeline_"
                        f"{_pf_slug}_{_pf_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_preflight_timeline_json",
                )
            with st.expander("Raw preflight JSON", expanded=False):
                st.json(_pf)
