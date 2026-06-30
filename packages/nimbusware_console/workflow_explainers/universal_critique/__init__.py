from nimbusware_console.explainer_core.generic_workflow_explainer import install_explainer_metrics
from nimbusware_console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_enabled_false_count as _universal_critique_top_level_enabled_false_count,
)
from nimbusware_console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_enabled_true_count as _universal_critique_top_level_enabled_true_count,
)
from nimbusware_console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_enabled_unset_mapping_count as _universal_critique_top_level_enabled_unset_mapping_count,
)
from nimbusware_console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_list_child_count as _universal_critique_top_level_list_child_count,
)
from nimbusware_console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_mapping_child_count as _universal_critique_top_level_mapping_child_count,
)
from nimbusware_console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_nonempty_count as _universal_critique_top_level_nonempty_count,
)
from nimbusware_console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_scalar_leaf_count as _universal_critique_top_level_scalar_leaf_count,
)
from nimbusware_console.explainer_core.universal_critique_counts import (
    universal_critique_yaml_value_nonempty as _universal_critique_yaml_value_nonempty,
)
from nimbusware_console.explainer_core.workflow_explainer_registry import (
    install_package_workflow_explainer_exports,
)
from nimbusware_console.explainer_core.workflow_exports import (
    install_named_workflow_explainer_exports,
)
from nimbusware_console.workflow_explainers.universal_critique.captions import (
    _UNIVERSAL_CRITIQUE_STAGE_KEYS_CAP,
    universal_critique_default_enabled_caption,
    universal_critique_enabled_stages_caption,
    universal_critique_env_override_summary_caption,
    universal_critique_workflow_yaml_bytes_caption,
    universal_critique_workflow_yaml_relpath_caption,
    universal_critique_yaml_enabled_bucket_caption,
    universal_critique_yaml_present_caption,
    universal_critique_yaml_stage_keys_caption,
    universal_critique_yaml_top_level_enabled_false_count_caption,
    universal_critique_yaml_top_level_enabled_true_count_caption,
    universal_critique_yaml_top_level_list_child_count_caption,
    universal_critique_yaml_top_level_mapping_child_count_caption,
    universal_critique_yaml_top_level_nonempty_count_caption,
)
from nimbusware_console.workflow_explainers.universal_critique.compare import (
    universal_critique_env_override_deltas,
    universal_critique_workflow_vs_timeline_rows,
)
from nimbusware_console.workflow_explainers.universal_critique.payload import (
    universal_critique_workflow_explainer_payload,
)

install_explainer_metrics("universal_critique", globals())

install_package_workflow_explainer_exports(
    globals(), "universal_critique"
)  # workflow-explainer-exports
