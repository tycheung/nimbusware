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
import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

import yaml

from hermes_extensions.personas import ALLOWED_SHELVES
from hermes_extensions.phase2 import ModuleIntegrator
from hermes_orchestrator.integrator_gate import (
    integrator_gate_workflow_enabled,
    load_bundle_tags_for_bundle_id,
    load_integrator_gate_emit_enabled,
    parse_integrator_gate_min_score_to_pass,
    parse_integrator_gate_project_tags,
)

from nimbusware_console.integrator_preview.parse import (
    ALLOWED_FULL_WORKFLOW_ROOT_KEYS,
    _FULL_WORKFLOW_MAPPING_KEYS,
)
from nimbusware_console.integrator_preview.merge.diff import (
    _SUBTREE_CHANGED_FIELDS_CAPTION_MAX_KEYS,
    _SUBTREE_CHANGED_KEYS_CAP,
)
def full_workflow_merge_subtree_changed_fields_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    subtrees = diff.get("subtree_field_diffs")
    if not isinstance(subtrees, Mapping):
        return None

    def _segment(block_name: str) -> str | None:
        block = subtrees.get(block_name)
        if not isinstance(block, Mapping):
            return None
        raw = block.get("changed_keys")
        if not isinstance(raw, list) or not raw:
            return None
        cleaned: set[str] = set()
        for entry in raw:
            if not isinstance(entry, str):
                continue
            trimmed = entry.strip()
            if trimmed:
                cleaned.add(trimmed)
        if not cleaned:
            return None
        ordered = sorted(cleaned)
        cap = _SUBTREE_CHANGED_FIELDS_CAPTION_MAX_KEYS
        visible = ordered[:cap]
        overflow = len(ordered) - len(visible)
        inner = ", ".join(visible)
        if overflow > 0:
            inner += f" (+{overflow} more)"
        return f"{block_name} ({inner})"

    parts: list[str] = []
    for name in ("integrator_gate", "agent_evaluator"):
        seg = _segment(name)
        if seg:
            parts.append(seg)
    if not parts:
        return None
    return "Subtree changed fields: " + ", ".join(parts) + "."


def full_workflow_merge_subtree_removed_fields_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    subtrees = diff.get("subtree_field_diffs")
    if not isinstance(subtrees, Mapping):
        return None

    def _segment(block_name: str) -> str | None:
        block = subtrees.get(block_name)
        if not isinstance(block, Mapping):
            return None
        raw = block.get("removed_keys")
        if not isinstance(raw, list) or not raw:
            return None
        cleaned: set[str] = set()
        for entry in raw:
            if not isinstance(entry, str):
                continue
            trimmed = entry.strip()
            if trimmed:
                cleaned.add(trimmed)
        if not cleaned:
            return None
        ordered = sorted(cleaned)
        cap = _SUBTREE_CHANGED_FIELDS_CAPTION_MAX_KEYS
        visible = ordered[:cap]
        overflow = len(ordered) - len(visible)
        inner = ", ".join(visible)
        if overflow > 0:
            inner += f" (+{overflow} more)"
        return f"{block_name} ({inner})"

    parts: list[str] = []
    for name in ("integrator_gate", "agent_evaluator"):
        seg = _segment(name)
        if seg:
            parts.append(seg)
    if not parts:
        return None
    return "Subtree removed fields: " + ", ".join(parts) + "."


def full_workflow_merge_subtree_added_fields_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    subtrees = diff.get("subtree_field_diffs")
    if not isinstance(subtrees, Mapping):
        return None

    def _segment(block_name: str) -> str | None:
        block = subtrees.get(block_name)
        if not isinstance(block, Mapping):
            return None
        raw = block.get("added_keys")
        if not isinstance(raw, list) or not raw:
            return None
        cleaned: set[str] = set()
        for entry in raw:
            if not isinstance(entry, str):
                continue
            trimmed = entry.strip()
            if trimmed:
                cleaned.add(trimmed)
        if not cleaned:
            return None
        ordered = sorted(cleaned)
        cap = _SUBTREE_CHANGED_FIELDS_CAPTION_MAX_KEYS
        visible = ordered[:cap]
        overflow = len(ordered) - len(visible)
        inner = ", ".join(visible)
        if overflow > 0:
            inner += f" (+{overflow} more)"
        return f"{block_name} ({inner})"

    parts: list[str] = []
    for name in ("integrator_gate", "agent_evaluator"):
        seg = _segment(name)
        if seg:
            parts.append(seg)
    if not parts:
        return None
    return "Subtree added fields: " + ", ".join(parts) + "."


