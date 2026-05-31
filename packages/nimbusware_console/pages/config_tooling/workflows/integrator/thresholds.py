from __future__ import annotations

from pathlib import Path

from nimbusware_console.components.explainer_panel import render_explainer_export_downloads
from nimbusware_console.components.workflow_explainer_helpers import (
    render_workflow_explainer_metrics_panel,
)
from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def render_thresholds_section(*, repo_root: Path, workflow_profile: str | None) -> None:
    with st.expander("Integrator thresholds & gate emission (fo133)", expanded=False):
        st.caption(
            "Read-only: **pipeline** ``min_score_to_pass`` resolution (matches gate emission) vs "
            "**Streamlit preview** (pasted fragment can change preview only), plus whether a "
            "``gate.decision.emitted`` would be written given ``HERMES_EMIT_INTEGRATOR_GATE``, "
            "``configs/integrator/thresholds.yaml`` **enabled**, and workflow "
            "``integrator_gate.enabled``."
        )
        _thr_payload = integrator_threshold_explainer_payload(
            repo_root,
            workflow_profile=workflow_profile,
            pasted_yaml=str(st.session_state.get("hermes_integrator_paste_yaml", "")),
        )
        _thr_expl_metrics, _thr_expl_metric_rows = render_workflow_explainer_metrics_panel(
            _thr_payload,
            metrics_fn=integrator_threshold_explainer_operator_metrics,
            metrics_table_rows_fn=integrator_threshold_explainer_operator_metrics_table_rows,
            metrics_caption_fn=integrator_threshold_explainer_operator_metrics_caption,
            filename_slug=integrator_threshold_explainer_operator_metrics_export_filename_slug(),
            json_label="Download integrator threshold operator metrics JSON",
            csv_label="Download integrator threshold operator metrics CSV",
            json_download_key="hermes_dl_integrator_threshold_explainer_metrics_json",
            csv_download_key="hermes_dl_integrator_threshold_explainer_metrics_csv",
        )
        _thr_emit_cap = integrator_threshold_gate_emission_caption(_thr_payload)
        if _thr_emit_cap:
            st.caption(_thr_emit_cap)
        _thr_min_cap = integrator_threshold_min_score_agreement_caption(_thr_payload)
        if _thr_min_cap:
            st.caption(_thr_min_cap)
        _thr_tags_cap = integrator_threshold_project_tags_caption(_thr_payload)
        if _thr_tags_cap:
            st.caption(_thr_tags_cap)
        _thr_paste_cap = integrator_threshold_paste_parse_caption(_thr_payload)
        if _thr_paste_cap:
            st.caption(_thr_paste_cap)
        _thr_thr_ver_cap = integrator_threshold_thresholds_yaml_version_caption(
            _thr_payload,
        )
        if _thr_thr_ver_cap:
            st.caption(_thr_thr_ver_cap)
        _thr_ty = _thr_payload.get("thresholds_yaml")
        _thr_ver = (
            "—"
            if not isinstance(_thr_ty, dict)
            or _thr_ty.get("top_level_version_int") is None
            else str(_thr_ty.get("top_level_version_int"))
        )
        _thr_bytes = (
            "—"
            if not isinstance(_thr_ty, dict)
            or _thr_ty.get("thresholds_yaml_file_bytes") is None
            else str(_thr_ty.get("thresholds_yaml_file_bytes"))
        )
        _thr_rows = [
            {
                "field": "configs/integrator/thresholds.yaml version (int)",
                "value": _thr_ver,
            },
            {
                "field": "configs/integrator/thresholds.yaml on-disk size (bytes)",
                "value": _thr_bytes,
            },
            {
                "field": "pipeline effective min_score_to_pass",
                "value": str(_thr_payload.get("pipeline_effective_min_score_to_pass")),
            },
            {
                "field": "streamlit preview effective min_score_to_pass",
                "value": str(_thr_payload.get("streamlit_preview_effective_min_score_to_pass")),
            },
            {
                "field": "would_emit integrator gate event",
                "value": str(
                    _thr_payload.get("gate_event_emission", {}).get(
                        "would_emit_integrator_gate_event",
                    ),
                ),
            },
            {
                "field": "workflow integrator_gate project_tags list length",
                "value": "—"
                if _thr_payload.get("workflow_integrator_gate", {}).get(
                    "project_tags_list_length",
                )
                is None
                else str(
                    _thr_payload.get("workflow_integrator_gate", {}).get(
                        "project_tags_list_length",
                    ),
                ),
            },
        ]
        st.dataframe(_thr_rows, use_container_width=True, hide_index=True)
        _thr_expl_rows = integrator_threshold_explainer_table_rows(_thr_payload)
        if _thr_expl_rows:
            render_explainer_export_downloads(
                json_text=integrator_threshold_explainer_export_json(_thr_payload),
                csv_text=integrator_threshold_explainer_table_rows_csv(_thr_expl_rows),
                filename_slug=integrator_threshold_export_filename_slug(),
                json_label="Download integrator threshold explainer JSON",
                csv_label="Download integrator threshold explainer CSV",
                json_download_key="hermes_dl_integrator_threshold_explainer_json",
                csv_download_key="hermes_dl_integrator_threshold_explainer_csv",
            )
        with st.expander("Raw threshold explainer JSON", expanded=False):
            st.json(_thr_payload)
