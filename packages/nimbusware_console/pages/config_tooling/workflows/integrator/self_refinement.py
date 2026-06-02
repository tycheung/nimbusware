from __future__ import annotations

from pathlib import Path

import streamlit as st

from nimbusware_console.components.explainer_panel import (
    render_explainer_export_downloads,
    render_operator_metrics_explainer,
)
from nimbusware_console.components.workflow_explainer_helpers import (
    render_workflow_explainer_metrics_panel,
)
from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def render_self_refinement_section(*, repo_root: Path, workflow_profile: str | None) -> None:
    with st.expander("Self-refinement (workflow + policy)", expanded=False):
        st.caption(
            "Read-only: workflow ``self_refinement`` from the **same** profile stem vs "
            "``configs/self_refinement/policy.yaml`` — **marker_merge** mirrors "
            "``_maybe_emit_self_refinement_stage_marker`` (emit when policy **or** workflow "
            "enables; version/description workflow wins when set). Env "
            "``HERMES_SELF_REFINEMENT_STAGE_MARKER`` in ``0``/``false``/``no`` suppresses "
            "the ``self_refinement:policy`` stage marker."
        )
        _sr_expl = self_refinement_workflow_explainer_payload(
            repo_root,
            workflow_profile=workflow_profile,
        )
        _sr_expl_metrics, _sr_expl_metric_rows = render_workflow_explainer_metrics_panel(
            _sr_expl,
            metrics_fn=self_refinement_workflow_explainer_operator_metrics,
            metrics_table_rows_fn=self_refinement_workflow_explainer_operator_metrics_table_rows,
            metrics_caption_fn=self_refinement_workflow_explainer_operator_metrics_caption,
            filename_slug=self_refinement_workflow_explainer_operator_metrics_export_filename_slug(),
            json_label="Download self-refinement operator metrics JSON",
            csv_label="Download self-refinement operator metrics CSV",
            json_download_key="hermes_dl_self_refinement_explainer_metrics_json",
            csv_download_key="hermes_dl_self_refinement_explainer_metrics_csv",
        )
        _sr_emit_cap = self_refinement_would_emit_marker_caption(
            _sr_expl.get("marker_merge"),
        )
        if _sr_emit_cap:
            st.caption(_sr_emit_cap)
        _sr_ver_cap = self_refinement_merged_version_caption(_sr_expl.get("marker_merge"))
        if _sr_ver_cap:
            st.caption(_sr_ver_cap)
        _sr_desc_cap = self_refinement_merged_description_preview_caption(
            _sr_expl.get("marker_merge"),
        )
        if _sr_desc_cap:
            st.caption(_sr_desc_cap)
        _sr_after_env_cap = self_refinement_would_emit_after_env_caption(
            _sr_expl.get("marker_merge"),
        )
        if _sr_after_env_cap:
            st.caption(_sr_after_env_cap)
        _sr_ungated_env_cap = self_refinement_ungated_loop_env_gate_caption(_sr_expl)
        if _sr_ungated_env_cap:
            st.caption(_sr_ungated_env_cap)
        _sr_disk_ver_cap = self_refinement_policy_yaml_disk_version_caption(_sr_expl)
        if _sr_disk_ver_cap:
            st.caption(_sr_disk_ver_cap)
        _sr_pol_bytes_cap = self_refinement_policy_yaml_file_bytes_caption(_sr_expl)
        if _sr_pol_bytes_cap:
            st.caption(_sr_pol_bytes_cap)
        _sr_raw_type_cap = self_refinement_workflow_yaml_raw_type_caption(_sr_expl)
        if _sr_raw_type_cap:
            st.caption(_sr_raw_type_cap)
        _sr_rows = [
            {
                "field": "self_refinement block in workflow YAML",
                "value": str(_sr_expl.get("self_refinement_yaml_present")),
            },
            {
                "field": "self_refinement (raw value Python type)",
                "value": "—"
                if _sr_expl.get("self_refinement_workflow_yaml_raw_type") is None
                else str(_sr_expl.get("self_refinement_workflow_yaml_raw_type")),
            },
            {
                "field": "self_refinement (mapping string-key count in YAML)",
                "value": "—"
                if _sr_expl.get("self_refinement_yaml_mapping_string_key_count") is None
                else str(_sr_expl.get("self_refinement_yaml_mapping_string_key_count")),
            },
            {
                "field": "policy.yaml on-disk size (bytes)",
                "value": "—"
                if _sr_expl.get("policy_yaml", {}).get("policy_yaml_file_bytes") is None
                else str(_sr_expl.get("policy_yaml", {}).get("policy_yaml_file_bytes")),
            },
            {
                "field": "policy.yaml top-level version (int, disk)",
                "value": "—"
                if _sr_expl.get("policy_yaml", {}).get("policy_yaml_top_level_version_int") is None
                else str(
                    _sr_expl.get("policy_yaml", {}).get("policy_yaml_top_level_version_int"),
                ),
            },
            {
                "field": "policy.yaml description length (chars)",
                "value": str(_sr_expl.get("policy_yaml", {}).get("description_char_len")),
            },
            {
                "field": "workflow self_refinement.enabled",
                "value": str(_sr_expl.get("workflow_self_refinement", {}).get("enabled")),
            },
            {
                "field": "policy.yaml enabled (disk)",
                "value": str(_sr_expl.get("policy_yaml", {}).get("enabled")),
            },
            {
                "field": "would_emit self_refinement:policy marker",
                "value": str(
                    _sr_expl.get("marker_merge", {}).get("would_emit_self_refinement_marker"),
                ),
            },
            {
                "field": "would_emit after env (effective)",
                "value": str(
                    _sr_expl.get("marker_merge", {}).get("would_emit_marker_after_env"),
                ),
            },
        ]
        st.dataframe(_sr_rows, use_container_width=True, hide_index=True)
        st.caption(
            "Optional **marker_merge vs timeline** table: paste either the top-level "
            "``self_refinement`` object **or** the full **GET /v1/runs/{id}/timeline** JSON "
            "(``events`` + summaries); the console extracts ``self_refinement`` when needed. "
            "Explainer values are predictive for the workflow profile above; timeline values "
            "are the last observed snapshot. When present, **``marker_count``** matches the "
            "timeline read-model (Run detail / API)."
        )
        _sr_tl_raw = st.text_area(
            "Optional timeline or self_refinement JSON",
            value="",
            height=100,
            key="hermes_self_refinement_timeline_compare_json",
            placeholder='{"version": 1, "description": "…"} or full timeline JSON',
        )
        _sr_tl_sr: dict[str, Any] | None = None
        if _sr_tl_raw.strip():
            try:
                _sr_tl_parsed = json.loads(_sr_tl_raw)
                if isinstance(_sr_tl_parsed, dict):
                    _sr_tl_sr = self_refinement_snapshot_from_compare_paste(_sr_tl_parsed)
                else:
                    st.warning(
                        "Timeline comparison JSON must be a single object (dict), "
                        "not a list or scalar.",
                    )
            except json.JSONDecodeError as exc:
                st.warning(f"Invalid JSON ({exc.msg}).")
        _sr_compare_rows = self_refinement_marker_merge_vs_timeline_rows(
            _sr_expl.get("marker_merge"),
            _sr_tl_sr,
        )
        st.dataframe(_sr_compare_rows, use_container_width=True, hide_index=True)
        _sr_marker_merge = _sr_expl.get("marker_merge")
        if isinstance(_sr_marker_merge, dict):
            _sr_compare_snap = self_refinement_marker_merge_compare_snapshot(
                _sr_marker_merge,
                _sr_tl_sr,
            )
            render_operator_metrics_explainer(
                caption=None,
                table_rows=None,
                json_text=self_refinement_marker_merge_compare_export_json(
                    _sr_compare_snap,
                ),
                csv_text=self_refinement_marker_merge_compare_table_rows_csv(
                    _sr_compare_rows,
                ),
                filename_slug=self_refinement_marker_merge_compare_export_filename_slug(),
                json_label="Download marker compare JSON",
                csv_label="Download marker compare CSV",
                json_download_key="hermes_dl_self_refinement_marker_compare_json",
                csv_download_key="hermes_dl_self_refinement_marker_compare_csv",
            )
        with st.expander("Raw marker_merge vs pasted timeline JSON", expanded=False):
            st.json(
                {
                    "marker_merge": _sr_expl.get("marker_merge"),
                    "timeline_self_refinement": _sr_tl_sr,
                },
            )
        _sr_err = _sr_expl.get("load_error")
        if isinstance(_sr_err, str) and _sr_err.strip():
            st.warning(str(_sr_err))
        _sr_expl_rows = self_refinement_explainer_table_rows(_sr_expl)
        if _sr_expl_rows:
            render_explainer_export_downloads(
                json_text=self_refinement_explainer_export_json(_sr_expl),
                csv_text=self_refinement_explainer_table_rows_csv(_sr_expl_rows),
                filename_slug=self_refinement_export_filename_slug(),
                json_label="Download self-refinement explainer JSON",
                csv_label="Download self-refinement explainer CSV",
                json_download_key="hermes_dl_self_refinement_explainer_json",
                csv_download_key="hermes_dl_self_refinement_explainer_csv",
            )
        with st.expander("Raw self-refinement explainer JSON", expanded=False):
            st.json(_sr_expl)
