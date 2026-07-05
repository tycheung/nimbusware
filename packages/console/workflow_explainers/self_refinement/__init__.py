from console.explainer_core.bootstrap import bootstrap_standard_explainer
from console.workflow_explainers.self_refinement.captions import (
    self_refinement_merged_description_preview_caption,
    self_refinement_merged_version_caption,
    self_refinement_policy_yaml_disk_version_caption,
    self_refinement_policy_yaml_file_bytes_caption,
    self_refinement_workflow_yaml_raw_type_caption,
    self_refinement_would_emit_after_env_caption,
    self_refinement_would_emit_marker_caption,
)
from console.workflow_explainers.self_refinement.compare import (
    _timeline_self_refinement_description_len,
    _version_as_optional_int,
    self_refinement_marker_merge_vs_timeline_rows,
)
from console.workflow_explainers.self_refinement.marker_exports import (
    self_refinement_marker_merge_compare_export_filename_slug,
    self_refinement_marker_merge_compare_export_json,
    self_refinement_marker_merge_compare_export_json_rows,
    self_refinement_marker_merge_compare_snapshot,
    self_refinement_marker_merge_compare_table_rows_csv,
    self_refinement_workflow_explainer_operator_metrics_export_filename_slug,
)
from console.workflow_explainers.self_refinement.payload import (
    _load_policy_or_default,
    _marker_preview,
    _nimbusware_self_refinement_stage_marker_env_summary,
    _nimbusware_self_refinement_ungated_loop_env_summary,
    _self_refinement_stage_marker_env_disabled,
    self_refinement_ungated_loop_env_gate_caption,
    self_refinement_workflow_explainer_payload,
)

bootstrap_standard_explainer("self_refinement", globals())
