from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from nimbusware_config.workflow_read import (
    effective_universal_critique,
    parse_universal_critique_workflow_block,
)
from nimbusware_console.components.workflow_explainer_helpers import relative_under
from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_workflow_disk import load_workflow_profile_documents
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
    wf_key = str(workflow_profile).strip() if workflow_profile else ""
    wf_sel: str | None = wf_key if wf_key else None

    workflow_yaml_relpath: str | None = None
    load_error: str | None = None
    universal_critique_workflow_yaml_bytes: int | None = None
    universal_critique_yaml_present = False
    universal_critique_yaml_top_level_keys: list[str] = []
    universal_critique_yaml_top_level_nonempty_count = 0
    universal_critique_yaml_top_level_enabled_true_count = 0
    universal_critique_yaml_top_level_enabled_false_count = 0
    universal_critique_yaml_top_level_mapping_child_count = 0
    universal_critique_yaml_top_level_scalar_leaf_count = 0
    universal_critique_yaml_top_level_list_child_count = 0
    universal_critique_yaml_top_level_enabled_unset_mapping_count = 0

    mat = console_config_materializer(repo_root)
    if wf_sel:
        try:
            disk_raw, _effective_raw, wp, file_bytes = load_workflow_profile_documents(
                repo_root,
                wf_sel,
                materializer=mat,
            )
            workflow_yaml_relpath = relative_under(repo_root, wp)
            universal_critique_workflow_yaml_bytes = file_bytes
            uc = disk_raw.get("universal_critique")
            if isinstance(uc, dict):
                universal_critique_yaml_top_level_keys = sorted(str(k) for k in uc)
                universal_critique_yaml_present = bool(uc)
                universal_critique_yaml_top_level_nonempty_count = (
                    _universal_critique_top_level_nonempty_count(uc)
                )
                universal_critique_yaml_top_level_enabled_true_count = (
                    _universal_critique_top_level_enabled_true_count(uc)
                )
                universal_critique_yaml_top_level_enabled_false_count = (
                    _universal_critique_top_level_enabled_false_count(uc)
                )
                universal_critique_yaml_top_level_mapping_child_count = (
                    _universal_critique_top_level_mapping_child_count(uc)
                )
                universal_critique_yaml_top_level_scalar_leaf_count = (
                    _universal_critique_top_level_scalar_leaf_count(uc)
                )
                universal_critique_yaml_top_level_list_child_count = (
                    _universal_critique_top_level_list_child_count(uc)
                )
                universal_critique_yaml_top_level_enabled_unset_mapping_count = (
                    _universal_critique_top_level_enabled_unset_mapping_count(uc)
                )
        except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError) as exc:
            load_error = str(exc)

    wf_block = parse_universal_critique_workflow_block(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )
    eff = effective_universal_critique(
        repo_root,
        wf_sel,
        config_materializer=mat,
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
