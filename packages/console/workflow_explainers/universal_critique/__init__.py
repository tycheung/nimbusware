from console.explainer_core.bootstrap import bootstrap_standard_explainer
from console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_enabled_false_count as _universal_critique_top_level_enabled_false_count,
)
from console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_enabled_true_count as _universal_critique_top_level_enabled_true_count,
)
from console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_enabled_unset_mapping_count as _universal_critique_top_level_enabled_unset_mapping_count,
)
from console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_list_child_count as _universal_critique_top_level_list_child_count,
)
from console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_mapping_child_count as _universal_critique_top_level_mapping_child_count,
)
from console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_nonempty_count as _universal_critique_top_level_nonempty_count,
)
from console.explainer_core.universal_critique_counts import (
    universal_critique_top_level_scalar_leaf_count as _universal_critique_top_level_scalar_leaf_count,
)
from console.explainer_core.universal_critique_counts import (
    universal_critique_yaml_value_nonempty as _universal_critique_yaml_value_nonempty,
)
from console.workflow_explainers.universal_critique.captions import (
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
from console.workflow_explainers.universal_critique.compare import (
    universal_critique_env_override_deltas,
    universal_critique_workflow_vs_timeline_rows,
)
from console.workflow_explainers.universal_critique.payload import (
    universal_critique_workflow_explainer_payload,
)

bootstrap_standard_explainer("universal_critique", globals())
