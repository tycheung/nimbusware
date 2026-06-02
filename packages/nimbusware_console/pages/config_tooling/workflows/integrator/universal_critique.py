from __future__ import annotations

from pathlib import Path

import streamlit as st

from nimbusware_console.components.explainer_panel import render_explainer_export_downloads
from nimbusware_console.components.workflow_explainer_helpers import (
    render_workflow_explainer_metrics_panel,
)
from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def render_universal_critique_section(*, repo_root: Path, workflow_profile: str | None) -> None:
    with st.expander("Universal critique (workflow YAML)", expanded=False):
        st.caption(
            "Read-only: ``universal_critique`` from the **same** workflow profile as integrator "
            "preview — **yaml_only** is frozen file content; **effective_with_env** applies "
            "non-empty ``HERMES_*`` critique env overrides (same rules as the orchestrator)."
        )
        _uc_expl = universal_critique_workflow_explainer_payload(
            repo_root,
            workflow_profile=workflow_profile,
        )
        _uc_expl_metrics, _uc_expl_metric_rows = render_workflow_explainer_metrics_panel(
            _uc_expl,
            metrics_fn=universal_critique_workflow_explainer_operator_metrics,
            metrics_table_rows_fn=universal_critique_workflow_explainer_operator_metrics_table_rows,
            metrics_caption_fn=universal_critique_workflow_explainer_operator_metrics_caption,
            filename_slug=universal_critique_workflow_explainer_operator_metrics_export_filename_slug(),
            json_label="Download universal critique operator metrics JSON",
            csv_label="Download universal critique operator metrics CSV",
            json_download_key="hermes_dl_universal_critique_explainer_metrics_json",
            csv_download_key="hermes_dl_universal_critique_explainer_metrics_csv",
        )
        _uc_enabled_cap = universal_critique_enabled_stages_caption(_uc_expl)
        if _uc_enabled_cap:
            st.caption(_uc_enabled_cap)
        _uc_default_cap = universal_critique_default_enabled_caption(_uc_expl)
        if _uc_default_cap:
            st.caption(_uc_default_cap)
        _uc_present_cap = universal_critique_yaml_present_caption(_uc_expl)
        if _uc_present_cap:
            st.caption(_uc_present_cap)
        _uc_relpath_cap = universal_critique_workflow_yaml_relpath_caption(_uc_expl)
        if _uc_relpath_cap:
            st.caption(_uc_relpath_cap)
        _uc_bytes_cap = universal_critique_workflow_yaml_bytes_caption(_uc_expl)
        if _uc_bytes_cap:
            st.caption(_uc_bytes_cap)
        _uc_nonempty_cap = universal_critique_yaml_top_level_nonempty_count_caption(
            _uc_expl,
        )
        if _uc_nonempty_cap:
            st.caption(_uc_nonempty_cap)
        _uc_enabled_true_cap = universal_critique_yaml_top_level_enabled_true_count_caption(
            _uc_expl,
        )
        if _uc_enabled_true_cap:
            st.caption(_uc_enabled_true_cap)
        _uc_enabled_false_cap = universal_critique_yaml_top_level_enabled_false_count_caption(
            _uc_expl,
        )
        if _uc_enabled_false_cap:
            st.caption(_uc_enabled_false_cap)
        _uc_mapping_child_cap = universal_critique_yaml_top_level_mapping_child_count_caption(
            _uc_expl,
        )
        if _uc_mapping_child_cap:
            st.caption(_uc_mapping_child_cap)
        _uc_list_child_cap = universal_critique_yaml_top_level_list_child_count_caption(
            _uc_expl,
        )
        if _uc_list_child_cap:
            st.caption(_uc_list_child_cap)
        _uc_bucket_cap = universal_critique_yaml_enabled_bucket_caption(_uc_expl)
        if _uc_bucket_cap:
            st.caption(_uc_bucket_cap)
        _uc_stage_keys_cap = universal_critique_yaml_stage_keys_caption(_uc_expl)
        if _uc_stage_keys_cap:
            st.caption(_uc_stage_keys_cap)
        _uc_rows = [
            {
                "field": "universal_critique block in YAML",
                "value": str(_uc_expl.get("universal_critique_yaml_present")),
            },
            {
                "field": "universal_critique YAML top-level keys",
                "value": ", ".join(_uc_expl.get("universal_critique_yaml_top_level_keys") or [])
                or "—",
            },
            {
                "field": "universal_critique YAML top-level nonempty value count",
                "value": str(_uc_expl.get("universal_critique_yaml_top_level_nonempty_count")),
            },
            {
                "field": "universal_critique YAML top-level enabled: true subtree count",
                "value": str(
                    _uc_expl.get("universal_critique_yaml_top_level_enabled_true_count"),
                ),
            },
            {
                "field": "universal_critique YAML top-level enabled: false subtree count",
                "value": str(
                    _uc_expl.get("universal_critique_yaml_top_level_enabled_false_count"),
                ),
            },
            {
                "field": "universal_critique YAML top-level mapping child count",
                "value": str(
                    _uc_expl.get("universal_critique_yaml_top_level_mapping_child_count"),
                ),
            },
            {
                "field": "universal_critique YAML top-level scalar/null leaf count",
                "value": str(
                    _uc_expl.get("universal_critique_yaml_top_level_scalar_leaf_count"),
                ),
            },
            {
                "field": "universal_critique YAML top-level list child count",
                "value": str(
                    _uc_expl.get("universal_critique_yaml_top_level_list_child_count"),
                ),
            },
            {
                "field": "universal_critique YAML mapping children without enabled key",
                "value": str(
                    _uc_expl.get(
                        "universal_critique_yaml_top_level_enabled_unset_mapping_count",
                    ),
                ),
            },
            {
                "field": "workflow YAML file size (bytes, on disk)",
                "value": "—"
                if _uc_expl.get("universal_critique_workflow_yaml_bytes") is None
                else str(_uc_expl.get("universal_critique_workflow_yaml_bytes")),
            },
            {
                "field": "implementation LLM (effective)",
                "value": str(_uc_expl.get("effective_with_env", {}).get("impl_llm")),
            },
            {
                "field": "implementation stub (effective)",
                "value": str(_uc_expl.get("effective_with_env", {}).get("impl_stub")),
            },
            {
                "field": "test_writer enabled (effective)",
                "value": str(_uc_expl.get("effective_with_env", {}).get("tw_enabled")),
            },
            {
                "field": "planner enabled (effective)",
                "value": str(_uc_expl.get("effective_with_env", {}).get("pll_enabled")),
            },
        ]
        st.dataframe(_uc_rows, use_container_width=True, hide_index=True)
        _uc_delta = universal_critique_env_override_deltas(_uc_expl)
        if _uc_delta:
            st.caption("Env overrides vs frozen YAML (non-matching knobs only).")
            st.dataframe(_uc_delta, use_container_width=True, hide_index=True)
        _uc_delta_cap = universal_critique_env_override_summary_caption(_uc_expl)
        if _uc_delta_cap:
            st.caption(_uc_delta_cap)
        _uc_err = _uc_expl.get("load_error")
        if isinstance(_uc_err, str) and _uc_err.strip():
            st.warning(str(_uc_err))
        _uc_expl_rows = universal_critique_explainer_table_rows(_uc_expl)
        if _uc_expl_rows:
            render_explainer_export_downloads(
                json_text=universal_critique_explainer_export_json(_uc_expl),
                csv_text=universal_critique_explainer_table_rows_csv(_uc_expl_rows),
                filename_slug=universal_critique_export_filename_slug(),
                json_label="Download universal critique explainer JSON",
                csv_label="Download universal critique explainer CSV",
                json_download_key="hermes_dl_universal_critique_explainer_json",
                csv_download_key="hermes_dl_universal_critique_explainer_csv",
            )
        with st.expander("Raw universal critique explainer JSON", expanded=False):
            st.json(_uc_expl)
        st.caption(
            "Optional **workflow vs timeline** table: paste the top-level "
            "``universal_critique`` object **or** full **GET /v1/runs/{id}/timeline** JSON. "
            "Workflow counts are from the selected profile YAML; timeline values are "
            "observed gate rollups."
        )
        _uc_tl_raw = st.text_area(
            "Optional timeline or universal_critique JSON",
            value="",
            height=100,
            key="hermes_universal_critique_timeline_compare_json",
            placeholder='{"fail_count": 0, "stage_count": 2, "stages": [...]} or full timeline',
        )
        _uc_tl_uc: dict[str, Any] | None = None
        if _uc_tl_raw.strip():
            try:
                _uc_tl_parsed = json.loads(_uc_tl_raw)
                if isinstance(_uc_tl_parsed, dict):
                    _uc_tl_uc = universal_critique_snapshot_from_compare_paste(
                        _uc_tl_parsed,
                    )
                else:
                    st.warning(
                        "Timeline comparison JSON must be a single object (dict), "
                        "not a list or scalar.",
                    )
            except json.JSONDecodeError as exc:
                st.warning(f"Invalid JSON ({exc.msg}).")
        _uc_compare_rows = universal_critique_workflow_vs_timeline_rows(
            _uc_expl,
            _uc_tl_uc,
        )
        st.dataframe(_uc_compare_rows, use_container_width=True, hide_index=True)
        with st.expander("Raw universal_critique vs pasted timeline JSON", expanded=False):
            st.json(
                {
                    "workflow_explainer": _uc_expl,
                    "timeline_universal_critique": _uc_tl_uc,
                },
            )
