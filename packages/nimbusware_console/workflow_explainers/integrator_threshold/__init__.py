from nimbusware_console.explainer_core.generic_workflow_explainer import install_explainer_metrics
from nimbusware_console.explainer_core.workflow_explainer_registry import (
    install_package_workflow_explainer_exports,
)
from nimbusware_console.explainer_core.workflow_exports import (
    install_named_workflow_explainer_exports,
)
from nimbusware_console.workflow_explainers.integrator_threshold.captions import (
    _INTEGRATOR_THRESHOLD_PASTE_PARSE_ERROR_CAP,
    integrator_threshold_gate_emission_caption,
    integrator_threshold_min_score_agreement_caption,
    integrator_threshold_paste_parse_caption,
    integrator_threshold_project_tags_caption,
    integrator_threshold_thresholds_yaml_version_caption,
)
from nimbusware_console.workflow_explainers.integrator_threshold.payload import (
    integrator_threshold_explainer_payload,
)
from nimbusware_console.workflow_explainers.integrator_threshold.snapshots import (
    _emit_integrator_gate_breakdown,
    _env_min_score_to_pass_breakdown,
    _thresholds_disk_snapshot,
    _thresholds_snapshot,
)

install_explainer_metrics("integrator_threshold", globals())

install_package_workflow_explainer_exports(
    globals(), "integrator_threshold"
)  # workflow-explainer-exports
