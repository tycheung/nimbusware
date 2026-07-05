from console.explainer_core.bootstrap import bootstrap_standard_explainer
from console.explainer_core.time import age_seconds_utc as _age_seconds_utc
from console.explainer_core.workflow_explainer_registry import (
    install_package_workflow_explainer_exports,
)
from console.workflow_explainers.escalation_suppress.captions import (
    escalation_policy_yaml_age_caption,
    escalation_policy_yaml_anti_deadlock_min_progress_caption,
    escalation_policy_yaml_anti_deadlock_shape_caption,
    escalation_policy_yaml_deadlock_minutes_caption,
    escalation_policy_yaml_file_bytes_caption,
    escalation_policy_yaml_key_count_caption,
    escalation_policy_yaml_keys_sample_caption,
    escalation_policy_yaml_max_retries_caption,
    escalation_policy_yaml_mtime_caption,
    escalation_policy_yaml_relpath_caption,
    escalation_policy_yaml_top_level_kinds_caption,
    escalation_policy_yaml_verification_shape_caption,
    escalation_policy_yaml_version_caption,
    escalation_suppress_flag_caption,
    escalation_yaml_key_present_caption,
)
from console.workflow_explainers.escalation_suppress.payload import (
    escalation_suppress_workflow_explainer_payload,
)
from console.workflow_explainers.escalation_suppress.policy_tables import (
    _escalation_policy_keys_rows_from_list,
    escalation_policy_export_filename_slug,
    escalation_policy_yaml_keys_all_export_json,
    escalation_policy_yaml_keys_all_table_rows,
    escalation_policy_yaml_keys_all_table_rows_csv,
    escalation_policy_yaml_top_level_kinds_export_json,
    escalation_policy_yaml_top_level_kinds_table_rows,
    escalation_policy_yaml_top_level_kinds_table_rows_csv,
)

bootstrap_standard_explainer("escalation_suppress", globals())

install_package_workflow_explainer_exports(
    globals(), "escalation_suppress"
)  # workflow-explainer-exports
