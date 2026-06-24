from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.field_caption import (
    payload_load_error_clear,
    payload_nonempty_str_caption,
    payload_nonneg_int_caption,
)


def _marker_merge_ready(payload: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    return payload if isinstance(payload, Mapping) else None


def _policy_yaml_ready(payload: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    body = payload_load_error_clear(payload)
    if body is None:
        return None
    pol = body.get("policy_yaml")
    return pol if isinstance(pol, Mapping) else None


def self_refinement_merged_version_caption(
    marker_merge: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonneg_int_caption(
        marker_merge,
        "merged_version",
        "Self-refinement merge preview: version=**{value}**.",
        guard=_marker_merge_ready,
        min_value=1,
    )


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
    return f"Self-refinement merge preview: description ({len_hint} chars): `{shown}`."


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
                "**NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER** kill-switch active."
            )
        return (
            "Self-refinement marker: **would not emit** "
            "(workflow ``self_refinement`` and disk policy gate off)."
        )
    return None


def self_refinement_workflow_yaml_raw_type_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonempty_str_caption(
        payload,
        "self_refinement_workflow_yaml_raw_type",
        "Self-refinement workflow YAML raw type: **{value}**.",
    )


def self_refinement_policy_yaml_file_bytes_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonneg_int_caption(
        payload,
        "policy_yaml_file_bytes",
        "Self-refinement policy.yaml on disk: **{value}** bytes.",
        guard=_policy_yaml_ready,
    )


def self_refinement_policy_yaml_disk_version_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonneg_int_caption(
        payload,
        "policy_yaml_top_level_version_int",
        "Self-refinement policy.yaml on-disk version: **{value}**.",
        guard=_policy_yaml_ready,
        min_value=1,
    )
