from __future__ import annotations

from pathlib import Path

from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403
from nimbusware_console.pages.config_tooling.bundles.faiss_readiness import (
    render_faiss_readiness_section,
)



def _render_catalog_summary_panel(repo_root: Path) -> None:
    _bcat_sum = bundle_catalog_local_summary(repo_root)
    if _bcat_sum.get("has_catalog_yaml"):
        _bcat_sum_metrics = bundle_catalog_local_summary_operator_metrics(_bcat_sum)
        _bcat_sum_metrics_cap = bundle_catalog_local_summary_operator_metrics_caption(
            _bcat_sum_metrics,
        )
        if _bcat_sum_metrics_cap:
            st.caption(_bcat_sum_metrics_cap)
        _bcat_sum_metric_rows = bundle_catalog_local_summary_operator_metrics_table_rows(
            _bcat_sum_metrics,
        )
        if _bcat_sum_metric_rows:
            st.dataframe(_bcat_sum_metric_rows, use_container_width=True)
        _bcat_sum_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _bcat_sum_metrics_slug = (
            bundle_catalog_local_summary_operator_metrics_export_filename_slug()
        )
        _bcat_sum_metrics_json = bundle_catalog_local_summary_operator_metrics_export_json(
            _bcat_sum_metrics,
        )
        _bcat_sum_metrics_csv = bundle_catalog_local_summary_operator_metrics_table_rows_csv(
            _bcat_sum_metric_rows,
        )
        _bcat_sum_m_dl_json_col, _bcat_sum_m_dl_csv_col = st.columns(2)
        with _bcat_sum_m_dl_json_col:
            st.download_button(
                label="Download local catalog operator metrics JSON",
                data=_bcat_sum_metrics_json.encode("utf-8"),
                file_name=(
                    f"hermes_{_bcat_sum_metrics_slug}_"
                    f"{bundle_catalog_local_export_filename_slug(repo_root)}_"
                    f"{_bcat_sum_metrics_ts}.json"
                ),
                mime="application/json",
                key="hermes_dl_bundle_catalog_local_summary_metrics_json",
            )
        with _bcat_sum_m_dl_csv_col:
            if _bcat_sum_metrics_csv:
                st.download_button(
                    label="Download local catalog operator metrics CSV",
                    data=_bcat_sum_metrics_csv.encode("utf-8"),
                    file_name=(
                        f"hermes_{_bcat_sum_metrics_slug}_"
                        f"{bundle_catalog_local_export_filename_slug(repo_root)}_"
                        f"{_bcat_sum_metrics_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_bundle_catalog_local_summary_metrics_csv",
                )
        _bcat_sum_rows = bundle_catalog_local_summary_table_rows(_bcat_sum)
        if _bcat_sum_rows:
            _bcat_sum_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _bcat_sum_slug = bundle_catalog_local_summary_export_filename_slug()
            _bcat_sum_json = bundle_catalog_local_summary_export_json(_bcat_sum)
            _bcat_sum_csv = bundle_catalog_local_summary_table_rows_csv(_bcat_sum_rows)
            _bcat_sum_dl_json_col, _bcat_sum_dl_csv_col = st.columns(2)
            with _bcat_sum_dl_json_col:
                st.download_button(
                    label="Download local catalog summary JSON",
                    data=_bcat_sum_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_bcat_sum_slug}_"
                        f"{bundle_catalog_local_export_filename_slug(repo_root)}_{_bcat_sum_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_bundle_catalog_local_summary_json",
                )
            with _bcat_sum_dl_csv_col:
                if _bcat_sum_csv:
                    st.download_button(
                        label="Download local catalog summary CSV",
                        data=_bcat_sum_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_bcat_sum_slug}_"
                            f"{bundle_catalog_local_export_filename_slug(repo_root)}_{_bcat_sum_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_bundle_catalog_local_summary_csv",
                    )
        st.caption(
            f"**Local catalog**: ``{_bcat_sum['catalog_yaml_relpath']}`` — "
            f"{_bcat_sum['bundle_count']} bundle(s), "
            f"{_bcat_sum['distinct_tag_count']} distinct tag(s).",
        )
        _bcat_distinct_cap = bundle_catalog_distinct_tag_count_caption(repo_root)
        if _bcat_distinct_cap:
            st.caption(_bcat_distinct_cap)
        _bcat_tags = bundle_catalog_distinct_tags_sample(repo_root)
        if _bcat_tags:
            st.caption(
                "Top tags: ``" + "``, ``".join(_bcat_tags) + "``",
            )
        _bcat_top_counts = bundle_catalog_top_tag_counts(repo_root)
        if _bcat_top_counts:
            _bcat_top_cap = bundle_catalog_top_tag_caption(repo_root)
            if _bcat_top_cap:
                st.caption(_bcat_top_cap)
            st.dataframe(
                _bcat_top_counts,
                use_container_width=True,
                hide_index=True,
            )
            _bcat_top_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _bcat_top_slug = bundle_catalog_local_export_filename_slug(repo_root)
            _bcat_top_json = bundle_catalog_top_tag_counts_export_json(_bcat_top_counts)
            _bcat_top_csv = bundle_catalog_top_tag_counts_table_rows_csv(_bcat_top_counts)
            _bcat_top_dl_json_col, _bcat_top_dl_csv_col = st.columns(2)
            with _bcat_top_dl_json_col:
                st.download_button(
                    label="Download top tag counts JSON",
                    data=_bcat_top_json.encode("utf-8"),
                    file_name=(
                        f"hermes_bundle_catalog_top_tags_{_bcat_top_slug}_{_bcat_top_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_bundle_catalog_top_tags_json",
                )
            with _bcat_top_dl_csv_col:
                if _bcat_top_csv:
                    st.download_button(
                        label="Download top tag counts CSV",
                        data=_bcat_top_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_bundle_catalog_top_tags_{_bcat_top_slug}_{_bcat_top_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_bundle_catalog_top_tags_csv",
                    )
