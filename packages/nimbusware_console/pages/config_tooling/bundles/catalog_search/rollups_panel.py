from __future__ import annotations

from pathlib import Path

from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403


def _render_catalog_rollups_panel(repo_root: Path) -> None:
    _bcat_sum = bundle_catalog_local_summary(repo_root)
    if not _bcat_sum.get("has_catalog_yaml"):
        return
    _bcat_total = int(_bcat_sum.get("bundle_count") or 0)
    if _bcat_total > 0:
        _bcat_count_cap = bundle_catalog_bundle_count_caption(repo_root)
        if _bcat_count_cap:
            st.caption(_bcat_count_cap)
        _bcat_without = bundle_catalog_bundles_without_tags_count(repo_root)
        st.caption(
            f"Bundles without tags: {_bcat_without} of {_bcat_total}.",
        )
        if _bcat_without > 0:
            _bcat_without_rollup = bundle_catalog_bundles_without_tags_rollup(repo_root)
            _bcat_without_tags_metrics = (
                bundle_catalog_bundles_without_tags_rollup_operator_metrics(
                    _bcat_without_rollup,
                )
            )
            _bcat_without_tags_metrics_cap = (
                bundle_catalog_bundles_without_tags_rollup_operator_metrics_caption(
                    _bcat_without_tags_metrics,
                )
            )
            if _bcat_without_tags_metrics_cap:
                st.caption(_bcat_without_tags_metrics_cap)
            _bcat_without_tags_metric_rows = (
                bundle_catalog_bundles_without_tags_rollup_operator_metrics_table_rows(
                    _bcat_without_tags_metrics,
                )
            )
            if _bcat_without_tags_metric_rows:
                st.dataframe(
                    _bcat_without_tags_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
            _bcat_without_tags_metrics_ts = datetime.now(timezone.utc).strftime(
                "%Y%m%dT%H%M%SZ",
            )
            _bcat_without_tags_metrics_slug = (
                bundle_catalog_bundles_without_tags_rollup_operator_metrics_export_filename_slug()
            )
            _bcat_without_tags_metrics_json = (
                bundle_catalog_bundles_without_tags_rollup_operator_metrics_export_json(
                    _bcat_without_tags_metrics,
                )
            )
            _bcat_without_tags_metrics_csv = (
                bundle_catalog_bundles_without_tags_rollup_operator_metrics_table_rows_csv(
                    _bcat_without_tags_metric_rows,
                )
            )
            _bcat_without_tags_m_dl_json_col, _bcat_without_tags_m_dl_csv_col = (
                st.columns(2)
            )
            with _bcat_without_tags_m_dl_json_col:
                st.download_button(
                    label="Download bundles without tags rollup operator metrics JSON",
                    data=_bcat_without_tags_metrics_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_bcat_without_tags_metrics_slug}_"
                        f"{_bcat_without_tags_metrics_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_bundle_catalog_bundles_without_tags_rollup_metrics_json",
                )
            with _bcat_without_tags_m_dl_csv_col:
                if _bcat_without_tags_metrics_csv:
                    st.download_button(
                        label="Download bundles without tags rollup operator metrics CSV",
                        data=_bcat_without_tags_metrics_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_bcat_without_tags_metrics_slug}_"
                            f"{_bcat_without_tags_metrics_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_bundle_catalog_bundles_without_tags_rollup_metrics_csv",
                    )
            _bcat_without_rows = bundle_catalog_bundles_without_tags_rollup_table_rows(
                _bcat_without_rollup,
            )
            if _bcat_without_rows:
                _bcat_without_ts = datetime.now(timezone.utc).strftime(
                    "%Y%m%dT%H%M%SZ",
                )
                _bcat_without_slug = (
                    bundle_catalog_bundles_without_tags_rollup_export_filename_slug()
                )
                _bcat_without_repo_slug = bundle_catalog_local_export_filename_slug(
                    repo_root,
                )
                _bcat_without_json = bundle_catalog_bundles_without_tags_rollup_export_json(
                    _bcat_without_rollup,
                )
                _bcat_without_csv = (
                    bundle_catalog_bundles_without_tags_rollup_table_rows_csv(
                        _bcat_without_rows,
                    )
                )
                _bcat_without_dl_json_col, _bcat_without_dl_csv_col = st.columns(2)
                with _bcat_without_dl_json_col:
                    st.download_button(
                        label="Download bundles without tags rollup JSON",
                        data=_bcat_without_json.encode("utf-8"),
                        file_name=(
                            f"hermes_{_bcat_without_slug}_"
                            f"{_bcat_without_repo_slug}_{_bcat_without_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_bundle_catalog_bundles_without_tags_rollup_json",
                    )
                with _bcat_without_dl_csv_col:
                    if _bcat_without_csv:
                        st.download_button(
                            label="Download bundles without tags rollup CSV",
                            data=_bcat_without_csv.encode("utf-8"),
                            file_name=(
                                f"hermes_{_bcat_without_slug}_"
                                f"{_bcat_without_repo_slug}_{_bcat_without_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_bundle_catalog_bundles_without_tags_rollup_csv",
                        )
        _bcat_without_id = bundle_catalog_bundles_without_id_count(repo_root)
        _bcat_without_id_cap = bundle_catalog_bundles_without_id_caption(repo_root)
        if _bcat_without_id_cap:
            st.caption(_bcat_without_id_cap)
        if _bcat_without_id > 0:
            _bcat_without_id_rollup = bundle_catalog_bundles_without_id_rollup(repo_root)
            _bcat_without_id_metrics = (
                bundle_catalog_bundles_without_id_rollup_operator_metrics(
                    _bcat_without_id_rollup,
                )
            )
            _bcat_without_id_metrics_cap = (
                bundle_catalog_bundles_without_id_rollup_operator_metrics_caption(
                    _bcat_without_id_metrics,
                )
            )
            if _bcat_without_id_metrics_cap:
                st.caption(_bcat_without_id_metrics_cap)
            _bcat_without_id_metric_rows = (
                bundle_catalog_bundles_without_id_rollup_operator_metrics_table_rows(
                    _bcat_without_id_metrics,
                )
            )
            if _bcat_without_id_metric_rows:
                st.dataframe(
                    _bcat_without_id_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
            _bcat_without_id_metrics_ts = datetime.now(timezone.utc).strftime(
                "%Y%m%dT%H%M%SZ",
            )
            _bcat_without_id_metrics_slug = (
                bundle_catalog_bundles_without_id_rollup_operator_metrics_export_filename_slug()
            )
            _bcat_without_id_metrics_json = (
                bundle_catalog_bundles_without_id_rollup_operator_metrics_export_json(
                    _bcat_without_id_metrics,
                )
            )
            _bcat_without_id_metrics_csv = (
                bundle_catalog_bundles_without_id_rollup_operator_metrics_table_rows_csv(
                    _bcat_without_id_metric_rows,
                )
            )
            _bcat_without_id_m_dl_json_col, _bcat_without_id_m_dl_csv_col = st.columns(2)
            with _bcat_without_id_m_dl_json_col:
                st.download_button(
                    label="Download bundles without id rollup operator metrics JSON",
                    data=_bcat_without_id_metrics_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_bcat_without_id_metrics_slug}_"
                        f"{_bcat_without_id_metrics_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_bundle_catalog_bundles_without_id_rollup_metrics_json",
                )
            with _bcat_without_id_m_dl_csv_col:
                if _bcat_without_id_metrics_csv:
                    st.download_button(
                        label="Download bundles without id rollup operator metrics CSV",
                        data=_bcat_without_id_metrics_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_bcat_without_id_metrics_slug}_"
                            f"{_bcat_without_id_metrics_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_bundle_catalog_bundles_without_id_rollup_metrics_csv",
                    )
            _bcat_without_id_rows = bundle_catalog_bundles_without_id_rollup_table_rows(
                _bcat_without_id_rollup,
            )
            if _bcat_without_id_rows:
                _bcat_without_id_ts = datetime.now(timezone.utc).strftime(
                    "%Y%m%dT%H%M%SZ",
                )
                _bcat_without_id_slug = (
                    bundle_catalog_bundles_without_id_rollup_export_filename_slug()
                )
                _bcat_without_id_repo_slug = bundle_catalog_local_export_filename_slug(
                    repo_root,
                )
                _bcat_without_id_json = bundle_catalog_bundles_without_id_rollup_export_json(
                    _bcat_without_id_rollup,
                )
                _bcat_without_id_csv = (
                    bundle_catalog_bundles_without_id_rollup_table_rows_csv(
                        _bcat_without_id_rows,
                    )
                )
                _bcat_without_id_dl_json_col, _bcat_without_id_dl_csv_col = st.columns(2)
                with _bcat_without_id_dl_json_col:
                    st.download_button(
                        label="Download bundles without id rollup JSON",
                        data=_bcat_without_id_json.encode("utf-8"),
                        file_name=(
                            f"hermes_{_bcat_without_id_slug}_"
                            f"{_bcat_without_id_repo_slug}_{_bcat_without_id_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_bundle_catalog_bundles_without_id_rollup_json",
                    )
                with _bcat_without_id_dl_csv_col:
                    if _bcat_without_id_csv:
                        st.download_button(
                            label="Download bundles without id rollup CSV",
                            data=_bcat_without_id_csv.encode("utf-8"),
                            file_name=(
                                f"hermes_{_bcat_without_id_slug}_"
                                f"{_bcat_without_id_repo_slug}_{_bcat_without_id_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_bundle_catalog_bundles_without_id_rollup_csv",
                        )
        _bcat_without_tags_cap = bundle_catalog_bundles_without_tags_caption(repo_root)
        if _bcat_without_tags_cap:
            st.caption(_bcat_without_tags_cap)
    _bcat_ids = bundle_catalog_bundle_ids_sample(repo_root)
    if _bcat_ids:
        st.caption(
            "Bundle ids: ``" + "``, ``".join(_bcat_ids) + "``",
        )
    if _bcat_total > 0:
        _loc_bundles = bundle_catalog_local_bundles(repo_root)
        _loc_rows = bundle_catalog_local_bundles_table_rows(_loc_bundles)
        if _loc_rows:
            _loc_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _loc_slug = bundle_catalog_local_export_filename_slug(repo_root)
            _loc_json = bundle_catalog_local_bundles_export_json(_loc_bundles)
            _loc_csv = bundle_catalog_local_bundles_table_rows_csv(_loc_rows)
            _loc_dl_json_col, _loc_dl_csv_col = st.columns(2)
            with _loc_dl_json_col:
                st.download_button(
                    label="Download local catalog bundles JSON",
                    data=_loc_json.encode("utf-8"),
                    file_name=(
                        f"hermes_bundle_catalog_local_{_loc_slug}_{_loc_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_bundle_catalog_local_json",
                )
            with _loc_dl_csv_col:
                if _loc_csv:
                    st.download_button(
                        label="Download local catalog bundles CSV",
                        data=_loc_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_bundle_catalog_local_{_loc_slug}_{_loc_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_bundle_catalog_local_csv",
                    )
