from __future__ import annotations

import streamlit as st

from nimbusware_console.pages.run_detail._imports_common import (
    datetime,
    st,
    timezone,
)
from nimbusware_console.pages.run_detail._imports_display_b import (
    universal_critique_fail_stage_rows_csv,
    universal_critique_from_timeline,
    universal_critique_timeline_export_filename_slug,
    universal_critique_timeline_export_json,
    universal_critique_timeline_fail_count_caption,
    universal_critique_timeline_fail_stage_caption,
    universal_critique_timeline_fail_stage_rows,
    universal_critique_timeline_operator_metrics,
    universal_critique_timeline_operator_metrics_caption,
    universal_critique_timeline_operator_metrics_export_json,
    universal_critique_timeline_operator_metrics_table_rows,
    universal_critique_timeline_operator_metrics_table_rows_csv,
    universal_critique_timeline_stage_rows,
    universal_critique_timeline_stage_rows_csv,
)
from nimbusware_console.settings import repo_root


def _render_timeline_misc_universal_critique(run_id: str, data: dict, _wf_pick: str) -> None:
    _iroot = repo_root()
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
            _uc_tl_metrics_cap = universal_critique_timeline_operator_metrics_caption(
                _uc_tl_metrics,
            )
            if _uc_tl_metrics_cap:
                st.caption(_uc_tl_metrics_cap)
            _uc_tl_metric_rows = universal_critique_timeline_operator_metrics_table_rows(
                _uc_tl_metrics,
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
                _uc_tl_metrics_json = universal_critique_timeline_operator_metrics_export_json(
                    _uc_tl_metrics,
                )
                _uc_tl_metrics_csv = universal_critique_timeline_operator_metrics_table_rows_csv(
                    _uc_tl_metric_rows,
                )
                (
                    _uc_tl_metrics_dl_json_col,
                    _uc_tl_metrics_dl_csv_col,
                ) = st.columns(2)
                with _uc_tl_metrics_dl_json_col:
                    st.download_button(
                        label=("Download universal critique operator metrics JSON"),
                        data=_uc_tl_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_universal_critique_operator_metrics_"
                            f"{_uc_tl_slug}_{_uc_tl_ts}.json"
                        ),
                        mime="application/json",
                        key=("hermes_dl_universal_critique_operator_metrics_json"),
                    )
                with _uc_tl_metrics_dl_csv_col:
                    if _uc_tl_metrics_csv:
                        st.download_button(
                            label=("Download universal critique operator metrics CSV"),
                            data=_uc_tl_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_universal_critique_operator_metrics_"
                                f"{_uc_tl_slug}_{_uc_tl_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key=("hermes_dl_universal_critique_operator_metrics_csv"),
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
                            f"hermes_universal_critique_stages_{_uc_tl_slug}_{_uc_tl_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_universal_critique_stages_csv",
                    )
                with _uc_dl_csv_col:
                    st.download_button(
                        label="Download universal critique FAIL stages CSV",
                        data=_uc_fail_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_universal_critique_fail_stages_{_uc_tl_slug}_{_uc_tl_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_universal_critique_fail_csv",
                    )
                with _uc_dl_json_col:
                    st.download_button(
                        label="Download universal critique timeline JSON",
                        data=_uc_tl_json.encode("utf-8"),
                        file_name=(
                            f"hermes_universal_critique_timeline_{_uc_tl_slug}_{_uc_tl_ts}.json"
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
                            f"hermes_universal_critique_stages_{_uc_tl_slug}_{_uc_tl_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_universal_critique_stages_csv",
                    )
                with _uc_dl_json_col:
                    st.download_button(
                        label="Download universal critique timeline JSON",
                        data=_uc_tl_json.encode("utf-8"),
                        file_name=(
                            f"hermes_universal_critique_timeline_{_uc_tl_slug}_{_uc_tl_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_universal_critique_timeline_json",
                    )
            with st.expander("Raw universal_critique JSON", expanded=False):
                st.json(_uc_tl)
