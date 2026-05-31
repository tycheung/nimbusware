from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    FIELD_VALUE_COLUMNS,
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
    sequence_export_json,
    table_rows_csv,
)
import csv
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from io import StringIO
from pathlib import Path
from typing import Any

from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_workflow_disk import load_workflow_profile_documents
from hermes_extensions.self_refinement import (
    SelfRefinementPolicy,
    load_self_refinement_policy,
    self_refinement_policy_from_mapping,
)
from nimbusware_config.workflow_read import (
    SelfRefinementWorkflowBlock,
    load_yaml,
    parse_self_refinement_workflow_block,
    workflow_profile_dict,
    workflow_profile_path,
)
from nimbusware_console.components.workflow_explainer_helpers import relative_under

from nimbusware_console.self_refinement_workflow_explainer.env import (
    _hermes_self_refinement_stage_marker_env_summary,
    _hermes_self_refinement_ungated_loop_env_summary,
)
def self_refinement_merged_version_caption(
    marker_merge: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(marker_merge, Mapping):
        return None
    ver = marker_merge.get("merged_version")
    if not isinstance(ver, int) or isinstance(ver, bool) or ver < 1:
        return None
    return f"Self-refinement merge preview: version=**{ver}**."


def self_refinement_merged_description_preview_caption(
    marker_merge: Mapping[str, Any] | None,
    *,
    max_chars: int = 120,
) -> str | None:
    if not isinstance(marker_merge, Mapping):
        return None
    preview = marker_merge.get("merged_description_preview")
    if not isinstance(preview, str):
        return None
    text = preview.strip()
    if not text:
        return None
    raw_len = marker_merge.get("merged_description_len")
    if isinstance(raw_len, int) and not isinstance(raw_len, bool) and raw_len > 0:
        len_hint = raw_len
    else:
        len_hint = len(text)
    limit = max_chars if max_chars > 0 else 120
    shown = text if len(text) <= limit else text[:limit] + "…"
    return (
        f"Self-refinement merge preview: description ({len_hint} chars): "
        f"`{shown}`."
    )


def self_refinement_would_emit_after_env_caption(
    marker_merge: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(marker_merge, Mapping):
        return None
    after_env = marker_merge.get("would_emit_marker_after_env")
    if after_env is True:
        return "Self-refinement marker after env: **would emit**."
    if after_env is False:
        return "Self-refinement marker after env: **would not emit**."
    return None


def self_refinement_would_emit_marker_caption(
    marker_merge: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(marker_merge, Mapping):
        return None
    after_env = marker_merge.get("would_emit_marker_after_env")
    if after_env is True:
        would = marker_merge.get("would_emit_self_refinement_marker")
        if would is False:
            return (
                "Self-refinement marker: **would emit** after env "
                "(workflow/policy gate on; env kill-switch off)."
            )
        return (
            "Self-refinement marker: **would emit** "
            "``stage.started`` ``self_refinement:policy`` for this profile."
        )
    if after_env is False:
        would = marker_merge.get("would_emit_self_refinement_marker")
        if would is True:
            return (
                "Self-refinement marker: **would not emit** — "
                "**HERMES_SELF_REFINEMENT_STAGE_MARKER** kill-switch active."
            )
        return (
            "Self-refinement marker: **would not emit** "
            "(workflow ``self_refinement`` and disk policy gate off)."
        )
    return None


def self_refinement_workflow_yaml_raw_type_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    raw = payload.get("self_refinement_workflow_yaml_raw_type")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Self-refinement workflow YAML raw type: **{text}**."


def self_refinement_policy_yaml_file_bytes_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    pol = payload.get("policy_yaml")
    if not isinstance(pol, Mapping):
        return None
    raw = pol.get("policy_yaml_file_bytes")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Self-refinement policy.yaml on disk: **{raw}** bytes."


def self_refinement_policy_yaml_disk_version_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    pol = payload.get("policy_yaml")
    if not isinstance(pol, Mapping):
        return None
    raw = pol.get("policy_yaml_top_level_version_int")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        return None
    return f"Self-refinement policy.yaml on-disk version: **{raw}**."


