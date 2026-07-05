from console.components.operator_metrics import FIELD_VALUE_COLUMNS
from console.explainer_core.bootstrap import bootstrap_standard_explainer
from console.explainer_core.workflow_explainer_registry import (
    install_package_workflow_explainer_exports,
)
from console.workflow_explainers.security_scan_metadata.captions import (
    security_scan_metadata_effective_enabled_caption,
    security_scan_metadata_env_gate_caption,
    security_scan_metadata_mapping_key_count_caption,
    security_scan_metadata_workflow_yaml_file_bytes_caption,
    security_scan_metadata_workflow_yaml_relpath_caption,
    security_scan_metadata_workflow_yaml_string_key_count_caption,
    security_scan_metadata_workflow_yaml_version_caption,
    security_scan_metadata_yaml_effective_mismatch_caption,
    security_scan_metadata_yaml_raw_type_caption,
)
from console.workflow_explainers.security_scan_metadata.payload import (
    _nimbusware_attach_security_scan_metadata_env_summary,
    security_scan_metadata_workflow_explainer_payload,
)

_SECURITY_SCAN_METADATA_EXPLAINER_CSV_COLUMNS = FIELD_VALUE_COLUMNS
_SECURITY_SCAN_METADATA_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS = FIELD_VALUE_COLUMNS

bootstrap_standard_explainer("security_scan_metadata", globals())

install_package_workflow_explainer_exports(
    globals(), "security_scan_metadata"
)  # workflow-explainer-exports
