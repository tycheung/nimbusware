"""Config tooling — prune section."""

from __future__ import annotations

from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def render_workflows_prune_section() -> None:
    _prune_status_path = _resolve_prune_status_path()
    if _prune_status_path is None:
        return
    with st.expander("Prune status (scraper artifacts)", expanded=False):
        st.caption(
            "Reads the JSON file written by ``scripts/prune_scraper_artifacts.py "
            "--summary-path`` (or ``HERMES_prune_status_path``). Same shape as the "
            "``--json-summary`` stdout line plus a UTC ``wrote_at`` timestamp. "
            "Surfaces ``retention_alert_level``, ``retention_execution_mode``, "
            "object-store mirror prune counts, and ``retention_lifecycle_state`` when present."
        )
        st.caption(f"Effective status file: `{_prune_status_path}`")
        st.caption(prune_scraper_artifact_prune_workflow_caption())
        _prune_status = load_prune_status(_prune_status_path)
        _prune_schema_cap = prune_status_schema_version_caption(_prune_status)
        if _prune_schema_cap:
            st.caption(_prune_schema_cap)
        st.caption(prune_status_freshness_caption(_prune_status))
        _prune_age_cap = prune_status_age_since_wrote_at_caption(_prune_status)
        if _prune_age_cap:
            st.caption(_prune_age_cap)
        _prune_pat_cap = prune_status_pattern_filter_caption(_prune_status)
        if _prune_pat_cap:
            st.caption(_prune_pat_cap)
        _prune_max_age_cap = prune_status_max_age_days_caption(_prune_status)
        if _prune_max_age_cap:
            st.caption(_prune_max_age_cap)
        _prune_ret_alert_cap = prune_status_retention_alert_caption(_prune_status)
        if _prune_ret_alert_cap:
            st.caption(_prune_ret_alert_cap)
        _prune_ret_exec_cap = prune_status_retention_execution_caption(_prune_status)
        if _prune_ret_exec_cap:
            st.caption(_prune_ret_exec_cap)
        _prune_ret_policy_cap = prune_status_retention_policy_caption(_prune_status)
        if _prune_ret_policy_cap:
            st.caption(_prune_ret_policy_cap)
        _prune_os_cap = prune_status_object_store_prune_caption(_prune_status)
        if _prune_os_cap:
            st.caption(_prune_os_cap)
        _prune_dry_cap = prune_status_dry_run_caption(_prune_status)
        if _prune_dry_cap:
            st.caption(_prune_dry_cap)
        _prune_wrote_cap = prune_status_wrote_at_caption(_prune_status)
        if _prune_wrote_cap:
            st.caption(_prune_wrote_cap)
        _prune_outcome_cap = prune_status_pruned_outcome_caption(_prune_status)
        if _prune_outcome_cap:
            st.caption(_prune_outcome_cap)
        _prune_base_cap = prune_status_base_dir_caption(_prune_status)
        if _prune_base_cap:
            st.caption(_prune_base_cap)
        _prune_metrics = prune_status_operator_metrics(_prune_status)
        _prune_metrics_cap = prune_status_operator_metrics_caption(_prune_metrics)
        if _prune_metrics_cap:
            st.caption(_prune_metrics_cap)
        _prune_metric_rows = prune_status_operator_metrics_table_rows(_prune_metrics)
        _prune_rows = prune_status_summary_rows(_prune_status)
        _prune_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _prune_metrics_slug = prune_status_operator_metrics_export_filename_slug()
        if _prune_metric_rows:
            st.dataframe(
                _prune_metric_rows,
                use_container_width=True,
                hide_index=True,
            )
            _prune_metrics_json = prune_status_operator_metrics_export_json(
                _prune_metrics,
            )
            _prune_metrics_csv = prune_status_operator_metrics_table_rows_csv(
                _prune_metric_rows,
            )
            _prune_metrics_dl_json_col, _prune_metrics_dl_csv_col = st.columns(2)
            with _prune_metrics_dl_json_col:
                st.download_button(
                    label="Download prune status operator metrics JSON",
                    data=_prune_metrics_json.encode("utf-8"),
                    file_name=(
                        "hermes_prune_status_operator_metrics_"
                        f"{_prune_metrics_slug}_{_prune_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_prune_status_operator_metrics_json",
                )
            with _prune_metrics_dl_csv_col:
                if _prune_metrics_csv:
                    st.download_button(
                        label="Download prune status operator metrics CSV",
                        data=_prune_metrics_csv.encode("utf-8"),
                        file_name=(
                            "hermes_prune_status_operator_metrics_"
                            f"{_prune_metrics_slug}_{_prune_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_prune_status_operator_metrics_csv",
                    )
        if _prune_rows:
            st.dataframe(_prune_rows, use_container_width=True, hide_index=True)
        if _prune_status is not None:
            _prune_json = prune_status_export_json(_prune_status)
            _prune_csv = prune_status_summary_rows_csv(_prune_rows)
            _pr_dl1, _pr_dl2 = st.columns(2)
            with _pr_dl1:
                st.download_button(
                    label="Download prune status JSON",
                    data=_prune_json.encode("utf-8"),
                    file_name=f"hermes_prune_status_{_prune_ts}.json",
                    mime="application/json",
                    key="hermes_dl_prune_status_json",
                )
            with _pr_dl2:
                if _prune_csv:
                    st.download_button(
                        label="Download prune status summary CSV",
                        data=_prune_csv.encode("utf-8"),
                        file_name=f"hermes_prune_status_summary_{_prune_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_prune_status_summary_csv",
                    )
            with st.expander("Raw prune status JSON", expanded=False):
                st.json(_prune_status)
