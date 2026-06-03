from __future__ import annotations

import streamlit as st

from nimbusware_console.pages.run_detail._imports_common import (
    datetime,
    st,
    timezone,
)
from nimbusware_console.pages.run_detail._imports_display_b import (
    security_scan_category_severity_caption,
    security_scan_finding_event_ids_caption,
    security_scan_linter_exit_codes_caption,
    security_scan_linter_failed_linters_caption,
    security_scan_linter_missing_linters_caption,
    security_scan_linter_nonzero_caption,
    security_scan_linter_ok_linters_caption,
    security_scan_linter_operator_metrics,
    security_scan_linter_operator_metrics_caption,
    security_scan_linter_operator_metrics_export_json,
    security_scan_linter_operator_metrics_table_rows,
    security_scan_linter_operator_metrics_table_rows_csv,
    security_scan_linter_status_rows,
    security_scan_linter_status_summary_caption,
    security_scan_linter_worst_status_caption,
    security_scan_metadata_timeline_workflow_alignment_caption,
    security_scan_metadata_workflow_explainer_payload,
    security_scan_occurred_at_age_caption,
    security_scan_on_verify_from_timeline,
    security_scan_on_verify_latest_export_filename_slug,
    security_scan_on_verify_latest_export_json,
    security_scan_on_verify_latest_operator_metrics,
    security_scan_on_verify_latest_operator_metrics_caption,
    security_scan_on_verify_latest_operator_metrics_export_json,
    security_scan_on_verify_latest_operator_metrics_table_rows,
    security_scan_on_verify_latest_operator_metrics_table_rows_csv,
    security_scan_on_verify_latest_summary_rows_csv,
    security_scan_on_verify_summary_rows,
    security_scan_snippet_length_caption,
    security_scan_snippet_line_count_caption,
)
from nimbusware_console.settings import repo_root


def _render_security_scan_on_verify(run_id: str, data: dict, _wf_pick: str) -> None:
    _iroot = repo_root()
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
            _ss_finding_metrics = security_scan_on_verify_latest_operator_metrics(_ss)
            _ss_finding_metrics_cap = security_scan_on_verify_latest_operator_metrics_caption(
                _ss_finding_metrics,
            )
            if _ss_finding_metrics_cap:
                st.caption(_ss_finding_metrics_cap)
            _ss_finding_metric_rows = security_scan_on_verify_latest_operator_metrics_table_rows(
                _ss_finding_metrics,
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
                        label=("Download security scan finding operator metrics JSON"),
                        data=_ss_finding_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_security_scan_finding_operator_metrics_"
                            f"{_ss_latest_slug}_{_ss_latest_ts}.json"
                        ),
                        mime="application/json",
                        key=("hermes_dl_security_scan_finding_operator_metrics_json"),
                    )
                with _ss_finding_metrics_dl_csv_col:
                    if _ss_finding_metrics_csv:
                        st.download_button(
                            label=("Download security scan finding operator metrics CSV"),
                            data=_ss_finding_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_security_scan_finding_operator_metrics_"
                                f"{_ss_latest_slug}_{_ss_latest_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key=("hermes_dl_security_scan_finding_operator_metrics_csv"),
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
                _ss_linter_summary = security_scan_linter_status_summary_caption(_ss)
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
                _ss_latest_slug = security_scan_on_verify_latest_export_filename_slug(
                    run_id.strip(),
                )
                _ss_linter_metrics = security_scan_linter_operator_metrics(_ss)
                _ss_linter_metrics_cap = security_scan_linter_operator_metrics_caption(
                    _ss_linter_metrics,
                )
                if _ss_linter_metrics_cap:
                    st.caption(_ss_linter_metrics_cap)
                _ss_linter_metric_rows = security_scan_linter_operator_metrics_table_rows(
                    _ss_linter_metrics,
                )
                if _ss_linter_metric_rows:
                    st.dataframe(
                        _ss_linter_metric_rows,
                        use_container_width=True,
                        hide_index=True,
                    )
                    _ss_linter_metrics_json = security_scan_linter_operator_metrics_export_json(
                        _ss_linter_metrics,
                    )
                    _ss_linter_metrics_csv = security_scan_linter_operator_metrics_table_rows_csv(
                        _ss_linter_metric_rows,
                    )
                    _ss_linter_metrics_dl_json_col, _ss_linter_metrics_dl_csv_col = st.columns(2)
                    with _ss_linter_metrics_dl_json_col:
                        st.download_button(
                            label=("Download security scan linter operator metrics JSON"),
                            data=_ss_linter_metrics_json.encode("utf-8"),
                            file_name=(
                                "hermes_security_scan_linter_operator_metrics_"
                                f"{_ss_latest_slug}_{_ss_latest_ts}.json"
                            ),
                            mime="application/json",
                            key=("hermes_dl_security_scan_linter_operator_metrics_json"),
                        )
                    with _ss_linter_metrics_dl_csv_col:
                        if _ss_linter_metrics_csv:
                            st.download_button(
                                label=("Download security scan linter operator metrics CSV"),
                                data=_ss_linter_metrics_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_security_scan_linter_operator_metrics_"
                                    f"{_ss_latest_slug}_{_ss_latest_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key=("hermes_dl_security_scan_linter_operator_metrics_csv"),
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
