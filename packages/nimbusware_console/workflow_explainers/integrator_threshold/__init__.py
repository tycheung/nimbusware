from nimbusware_console.explainer_core.workflow_explainer_registry import (
    install_package_workflow_explainer_exports,
)
from nimbusware_console.explainer_core.workflow_exports import (
    install_named_workflow_explainer_exports,
)
from nimbusware_console.explainer_core.workflow_metrics_spec import (
    install_workflow_metrics_from_spec,
    repo_explainer_spec,
)
from nimbusware_console.workflow_explainers.integrator_threshold.captions import (
    _INTEGRATOR_THRESHOLD_PASTE_PARSE_ERROR_CAP,
    integrator_threshold_gate_emission_caption,
    integrator_threshold_min_score_agreement_caption,
    integrator_threshold_paste_parse_caption,
    integrator_threshold_project_tags_caption,
    integrator_threshold_thresholds_yaml_version_caption,
)
from nimbusware_console.workflow_explainers.integrator_threshold.metrics_custom import (
    integrator_threshold_caption,
    integrator_threshold_caption_parts,
    integrator_threshold_post_process,
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

install_workflow_metrics_from_spec(
    globals(),
    repo_explainer_spec("integrator_threshold"),
    caption_parts_fn=integrator_threshold_caption_parts,
    post_process_metrics_fn=integrator_threshold_post_process,
    custom_caption_fn=integrator_threshold_caption,
)

install_package_workflow_explainer_exports(
    globals(), "integrator_threshold"
)  # workflow-explainer-exports
