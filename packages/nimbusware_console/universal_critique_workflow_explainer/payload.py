from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from nimbusware_config.workflow_read import (
    effective_universal_critique,
    parse_universal_critique_workflow_block,
)
from nimbusware_console.explainer_core.workflow_profile import (
    load_workflow_disk_snapshot,
    yaml_section,
)
from nimbusware_console.universal_critique_workflow_explainer.helpers import (
    _universal_critique_top_level_enabled_false_count,
    _universal_critique_top_level_enabled_true_count,
    _universal_critique_top_level_enabled_unset_mapping_count,
    _universal_critique_top_level_list_child_count,
    _universal_critique_top_level_mapping_child_count,
    _universal_critique_top_level_nonempty_count,
    _universal_critique_top_level_scalar_leaf_count,
)


def universal_critique_workflow_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
) -> dict[str, Any]:
    snap = load_workflow_disk_snapshot(repo_root, workflow_profile)
    wf_sel = snap.workflow_profile
    workflow_yaml_relpath = snap.workflow_yaml_relpath
    load_error = snap.load_error
    universal_critique_workflow_yaml_bytes = snap.file_bytes

    uc = yaml_section(snap.disk_doc, "universal_critique")
    universal_critique_yaml_present = bool(uc)
    universal_critique_yaml_top_level_keys = sorted(str(k) for k in uc) if uc else []
    universal_critique_yaml_top_level_nonempty_count = (
        _universal_critique_top_level_nonempty_count(uc) if uc else 0
    )
    universal_critique_yaml_top_level_enabled_true_count = (
        _universal_critique_top_level_enabled_true_count(uc) if uc else 0
    )
    universal_critique_yaml_top_level_enabled_false_count = (
        _universal_critique_top_level_enabled_false_count(uc) if uc else 0
    )
    universal_critique_yaml_top_level_mapping_child_count = (
        _universal_critique_top_level_mapping_child_count(uc) if uc else 0
    )
    universal_critique_yaml_top_level_scalar_leaf_count = (
        _universal_critique_top_level_scalar_leaf_count(uc) if uc else 0
    )
    universal_critique_yaml_top_level_list_child_count = (
        _universal_critique_top_level_list_child_count(uc) if uc else 0
    )
    universal_critique_yaml_top_level_enabled_unset_mapping_count = (
        _universal_critique_top_level_enabled_unset_mapping_count(uc) if uc else 0
    )

    wf_block = parse_universal_critique_workflow_block(
        repo_root,
        wf_sel,
        config_materializer=snap.materializer,
    )
    eff = effective_universal_critique(
        repo_root,
        wf_sel,
        config_materializer=snap.materializer,
    )

    return {
        "workflow_profile": wf_sel,
        "workflow_yaml_relpath": workflow_yaml_relpath,
        "load_error": load_error,
        "universal_critique_workflow_yaml_bytes": universal_critique_workflow_yaml_bytes,
        "universal_critique_yaml_present": universal_critique_yaml_present,
        "universal_critique_yaml_top_level_keys": universal_critique_yaml_top_level_keys,
        "universal_critique_yaml_top_level_nonempty_count": (
            universal_critique_yaml_top_level_nonempty_count
        ),
        "universal_critique_yaml_top_level_enabled_true_count": (
            universal_critique_yaml_top_level_enabled_true_count
        ),
        "universal_critique_yaml_top_level_enabled_false_count": (
            universal_critique_yaml_top_level_enabled_false_count
        ),
        "universal_critique_yaml_top_level_mapping_child_count": (
            universal_critique_yaml_top_level_mapping_child_count
        ),
        "universal_critique_yaml_top_level_scalar_leaf_count": (
            universal_critique_yaml_top_level_scalar_leaf_count
        ),
        "universal_critique_yaml_top_level_list_child_count": (
            universal_critique_yaml_top_level_list_child_count
        ),
        "universal_critique_yaml_top_level_enabled_unset_mapping_count": (
            universal_critique_yaml_top_level_enabled_unset_mapping_count
        ),
        "yaml_only": asdict(wf_block),
        "effective_with_env": asdict(eff),
    }
