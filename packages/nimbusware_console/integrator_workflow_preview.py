"""Module Integrator + workflow YAML preview helpers.

Read-only: validates ``integrator_gate``, ``agent_evaluator``, and **full-profile** workflow
roots; previews ``ModuleIntegrator`` scores against the local repo catalog. No writes
to ``configs/workflows/*.yaml``.
"""

from __future__ import annotations

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

# Top-level keys allowed when pasting a full workflow profile (union of shipped profiles).
_FULL_WORKFLOW_MAPPING_KEYS: frozenset[str] = frozenset(
    {
        "finding_fix_strictness",
        "network_egress",
        "scraper_fetch",
        "agent_evaluator",
        "integration_adapter_writer",
        "integrator_gate",
        "self_refinement",
        "universal_critique",
        "escalation",
    },
)
ALLOWED_FULL_WORKFLOW_ROOT_KEYS: frozenset[str] = frozenset(
    _FULL_WORKFLOW_MAPPING_KEYS | {"version", "security_scan_metadata_on_verify"},
)


def list_workflow_profile_keys(repo_root: Path) -> list[str]:
    """Basenames under ``configs/workflows`` (stem only, ``.yaml`` / ``.yml``)."""
    d = repo_root / "configs" / "workflows"
    if not d.is_dir():
        return []
    keys: set[str] = set()
    for p in d.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".yaml", ".yml"):
            continue
        stem = p.stem.strip()
        if stem and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", stem):
            keys.add(stem)
    return sorted(keys)


def parse_integrator_gate_yaml_fragment(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Parse YAML that is either a full workflow root or an ``integrator_gate``-only map."""
    raw = text.strip()
    if not raw:
        return None, []
    try:
        obj = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return None, [f"YAML parse error: {exc}"]
    if obj is None:
        return None, ["YAML document is null"]
    if not isinstance(obj, dict):
        return None, ["root must be a mapping"]
    ig = obj.get("integrator_gate")
    if isinstance(ig, dict):
        return dict(ig), []
    if any(k in obj for k in ("enabled", "min_score_to_pass", "project_tags")):
        return dict(obj), []
    return None, ["no integrator_gate mapping found (expected key or flat gate fields)"]


def validate_integrator_gate_block(block: dict[str, Any] | None) -> list[str]:
    """Structural checks for operator-authored fragments."""
    if not block:
        return []
    errs: list[str] = []
    if "min_score_to_pass" in block and block["min_score_to_pass"] is not None:
        try:
            v = float(block["min_score_to_pass"])
        except (TypeError, ValueError):
            errs.append("min_score_to_pass must be a number")
        else:
            if v < 0.0 or v > 1.0:
                errs.append("min_score_to_pass must be between 0 and 1")
    pt = block.get("project_tags")
    if pt is not None and not isinstance(pt, list):
        errs.append("project_tags must be a list of strings when set")
    elif isinstance(pt, list):
        for i, t in enumerate(pt):
            if not isinstance(t, (str, int, float, bool)) or isinstance(t, bool):
                errs.append(f"project_tags[{i}] must be string-like")
                break
    return errs


def parse_agent_evaluator_yaml_fragment(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Parse YAML that is either a full workflow root or an ``agent_evaluator``-only map."""
    raw = text.strip()
    if not raw:
        return None, []
    try:
        obj = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return None, [f"YAML parse error: {exc}"]
    if obj is None:
        return None, ["YAML document is null"]
    if not isinstance(obj, dict):
        return None, ["root must be a mapping"]
    ae = obj.get("agent_evaluator")
    if isinstance(ae, dict):
        return dict(ae), []
    keys = set(obj.keys())
    if keys and keys <= {
        "enabled",
        "persona_id",
        "auto_promote_probation",
        "auto_create_persona",
    }:
        return dict(obj), []
    return None, ["no agent_evaluator mapping found (expected key or flat enabled/persona_id)"]


def validate_agent_evaluator_block(block: dict[str, Any] | None) -> list[str]:
    """Structural checks for operator-authored ``agent_evaluator`` fragments."""
    if not block:
        return []
    errs: list[str] = []
    extra = set(block.keys()) - {
        "enabled",
        "persona_id",
        "auto_promote_probation",
        "auto_create_persona",
    }
    if extra:
        errs.append(f"unknown keys: {sorted(extra)}")
    if "enabled" in block and block["enabled"] is not None:
        ev = block["enabled"]
        if not isinstance(ev, (bool, int, float)):
            errs.append("enabled must be boolean or numeric when set")
    ap = block.get("auto_promote_probation")
    if ap is not None and not isinstance(ap, (bool, int, float)):
        errs.append("auto_promote_probation must be boolean or numeric when set")
    ac = block.get("auto_create_persona")
    if ac is not None:
        if not isinstance(ac, dict):
            errs.append("auto_create_persona must be a mapping when set")
        else:
            ac_extra = set(ac.keys()) - {"enabled", "shelf", "display_name"}
            if ac_extra:
                errs.append(f"auto_create_persona unknown keys: {sorted(ac_extra)}")
            ev_ac = ac.get("enabled")
            if ev_ac is not None and not isinstance(ev_ac, (bool, int, float)):
                errs.append("auto_create_persona.enabled must be boolean or numeric when set")
            sh = ac.get("shelf")
            if sh is not None and not isinstance(sh, (str, int, float)):
                errs.append("auto_create_persona.shelf must be string-like when set")
            elif isinstance(sh, str) and sh.strip() and sh.strip() not in ALLOWED_SHELVES:
                errs.append(
                    f"auto_create_persona.shelf must be one of {list(ALLOWED_SHELVES)} when set",
                )
            dn = ac.get("display_name")
            if dn is not None and not isinstance(dn, (str, int, float)):
                errs.append("auto_create_persona.display_name must be string-like when set")
    pid = block.get("persona_id")
    if pid is not None:
        if isinstance(pid, bool) or isinstance(pid, (list, dict)):
            errs.append("persona_id must be string or number when set")
        elif not isinstance(pid, (str, int, float)):
            errs.append("persona_id must be string-like when set")
    return errs


def parse_full_workflow_yaml_paste(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Parse a pasted full workflow root document (``configs/workflows/{profile}.yaml`` shape)."""
    raw = text.strip()
    if not raw:
        return None, ["pasted YAML is empty"]
    try:
        obj = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return None, [f"YAML parse error: {exc}"]
    if obj is None:
        return None, ["YAML document is null"]
    if not isinstance(obj, dict):
        return None, ["root must be a mapping"]
    return dict(obj), []


def validate_full_workflow_document(doc: dict[str, Any] | None) -> list[str]:
    """Structural validation for operator full-profile pastes (closed top-level key set)."""
    if not doc:
        return ["workflow document is empty"]
    errs: list[str] = []
    extra = set(doc) - ALLOWED_FULL_WORKFLOW_ROOT_KEYS
    if extra:
        errs.append(f"unknown top-level keys: {sorted(extra)}")
    ver = doc.get("version")
    if ver is not None:
        if isinstance(ver, bool) or not isinstance(ver, int) or ver < 1:
            errs.append("version must be an integer >= 1 when present")
    for mk in _FULL_WORKFLOW_MAPPING_KEYS:
        if mk not in doc:
            continue
        val = doc[mk]
        if val is None:
            continue
        if not isinstance(val, dict):
            errs.append(f"{mk} must be a mapping when present")
    ss = doc.get("security_scan_metadata_on_verify")
    if ss is not None and not isinstance(ss, (bool, int, float, str, dict)):
        errs.append("security_scan_metadata_on_verify must be scalar or mapping when set")
    ig = doc.get("integrator_gate")
    if isinstance(ig, dict):
        errs.extend(validate_integrator_gate_block(ig))
    ae = doc.get("agent_evaluator")
    if isinstance(ae, dict):
        errs.extend(validate_agent_evaluator_block(ae))
    return errs


def _shallow_mapping_field_diff(
    old: dict[str, Any],
    new: dict[str, Any],
) -> dict[str, Any]:
    """First-level key churn between two mappings (JSON-safe values)."""
    keys = sorted(set(old) | set(new))
    added = [k for k in keys if k not in old]
    removed = [k for k in keys if k not in new]
    changed: list[str] = []
    unchanged: list[str] = []
    for k in keys:
        if k in old and k in new:
            if old[k] != new[k]:
                changed.append(k)
            else:
                unchanged.append(k)
    entries: list[dict[str, Any]] = []
    for k in changed:
        entries.append({"field": k, "before": old[k], "after": new[k]})
    return {
        "added_keys": added,
        "removed_keys": removed,
        "changed_keys": changed,
        "unchanged_keys": unchanged,
        "changed_field_entries": entries,
    }


def full_workflow_merge_diff(
    before_disk: Mapping[str, Any] | None,
    merged_preview: Mapping[str, Any] | None,
    *,
    pasted_root: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize shallow full-profile merge: top-level key buckets + optional gate/AE fields.

    Pure helper for console dry-run: on-disk document vs merged preview from
    ``prepare_full_workflow_apply``.

    When ``pasted_root`` is a mapping, ``disk_only_top_level_keys`` lists keys present on
    ``before_disk`` but absent from the paste (they survive a shallow merge unchanged —
    operators pasting a partial root should review them). ``paste_only_top_level_keys``
    lists keys present in the paste but absent from ``before_disk`` (new sections the
    shallow merge would introduce). ``pasted_top_level_keys`` lists sorted top-level keys
    from the paste for quick diff orientation.
    """
    if before_disk is None or merged_preview is None:
        return {"error": "before_disk and merged_preview are required"}
    if not isinstance(before_disk, dict) or not isinstance(merged_preview, dict):
        return {"error": "before_disk and merged_preview must be dict mappings"}
    b: dict[str, Any] = before_disk
    m: dict[str, Any] = merged_preview
    all_keys = sorted(set(b) | set(m))
    added_top = [k for k in all_keys if k not in b]
    removed_top = [k for k in all_keys if k not in m]
    changed_top: list[str] = []
    unchanged_top: list[str] = []
    for k in all_keys:
        if k in b and k in m:
            if b[k] != m[k]:
                changed_top.append(k)
            else:
                unchanged_top.append(k)
    out: dict[str, Any] = {
        "added_top_level_keys": added_top,
        "removed_top_level_keys": removed_top,
        "changed_top_level_keys": changed_top,
        "unchanged_top_level_keys": unchanged_top,
    }
    if isinstance(pasted_root, dict):
        disk_only = sorted(str(k) for k in b if k not in pasted_root)
        out["disk_only_top_level_keys"] = disk_only
        paste_only = sorted(str(k) for k in pasted_root if k not in b)
        out["paste_only_top_level_keys"] = paste_only
        out["pasted_top_level_keys"] = sorted(str(k) for k in pasted_root)
    subtrees: dict[str, Any] = {}
    for k in ("integrator_gate", "agent_evaluator"):
        if k in changed_top and isinstance(b.get(k), dict) and isinstance(m.get(k), dict):
            subtrees[k] = _shallow_mapping_field_diff(b[k], m[k])
    if subtrees:
        out["subtree_field_diffs"] = subtrees
    return out


_SUBTREE_CHANGED_KEYS_CAP = 12
_SUBTREE_CHANGED_FIELDS_CAPTION_MAX_KEYS = 6


def full_workflow_merge_overview_caption(diff: Mapping[str, Any] | None) -> str | None:
    """Compact one-line top-level diff overview for the full-workflow dry-run.

    Counts ``added_top_level_keys`` / ``removed_top_level_keys`` /
    ``changed_top_level_keys`` / ``unchanged_top_level_keys`` (each treated as ``0`` when
    absent or not a list). Returns ``"Top-level: +<A> / -<R> / ~<C> / =<U>"`` when the
    diff is observable; returns ``None`` when ``diff`` is not a mapping or carries an
    ``error`` payload.
    """
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None

    def _count(key: str) -> int:
        raw = diff.get(key)
        return len(raw) if isinstance(raw, list) else 0

    added = _count("added_top_level_keys")
    removed = _count("removed_top_level_keys")
    changed = _count("changed_top_level_keys")
    unchanged = _count("unchanged_top_level_keys")
    return f"Top-level: +{added} / -{removed} / ~{changed} / ={unchanged}"


def full_workflow_merge_top_level_churn_count_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    """Count top-level keys that are added, removed, or value-changed (excludes ``=`` bucket)."""
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None

    def _count(key: str) -> int:
        raw = diff.get(key)
        return len(raw) if isinstance(raw, list) else 0

    n = (
        _count("added_top_level_keys")
        + _count("removed_top_level_keys")
        + _count("changed_top_level_keys")
    )
    return (
        "Dry-run top-level churn: **"
        f"{n}"
        "** key(s) added, removed, or value-changed (unchanged keys excluded)."
    )


def full_workflow_merge_diff_audit_fingerprint_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    """SHA-256 prefix + UTF-8 byte length of canonical merge-diff JSON (operator audit).

    Stable for the same logical diff so operators can compare dry-runs across sessions.
    Returns ``None`` when ``diff`` is not a mapping or carries an ``error`` key.
    """
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    try:
        payload = json.dumps(diff, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        return None
    raw = payload.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return (
        "Dry-run merge diff fingerprint: SHA-256 prefix "
        f"``{digest}`` over **{len(raw)}** UTF-8 bytes (canonical JSON)."
    )


def full_workflow_merge_unchanged_with_churn_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    """Surface how many top-level keys stay unchanged while some other root keys churn."""
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None

    def _count(key: str) -> int:
        raw = diff.get(key)
        return len(raw) if isinstance(raw, list) else 0

    churn = (
        _count("added_top_level_keys")
        + _count("removed_top_level_keys")
        + _count("changed_top_level_keys")
    )
    if churn <= 0:
        return None
    raw_u = diff.get("unchanged_top_level_keys")
    if not isinstance(raw_u, list) or not raw_u:
        return None
    return (
        f"While **{churn}** top-level key(s) add/remove/change, **{len(raw_u)}** root "
        "key(s) remain **unchanged** in this shallow merge preview."
    )


def full_workflow_merge_removed_top_level_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    """One-line caption naming the removed top-level keys.

    Mirror of :func:`full_workflow_merge_changed_top_level_caption` /
    :func:`full_workflow_merge_added_top_level_caption` for the
    ``removed_top_level_keys`` field. Returns
    ``"Removed top-level keys: <a>, <b>, <c>."`` when the field is a non-empty
    list with at least one usable string entry. Entries are whitespace-stripped,
    empty / non-string entries are skipped, and surviving entries are deduped +
    sorted alphabetically before joining.

    Returns ``None`` for:

    * non-mapping ``diff`` or ``error`` payloads,
    * missing / non-list ``removed_top_level_keys``,
    * an empty list, or
    * a list whose only entries are non-string / whitespace-only.

    Completes the added / changed / removed / unchanged caption quartet for the
    Top-level merge diff summary.
    """
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    raw = diff.get("removed_top_level_keys")
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
    return "Removed top-level keys: " + ", ".join(sorted(cleaned)) + "."


def full_workflow_merge_disk_only_top_level_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    """One-line caption naming top-level keys on disk that the paste omits.

    Returns ``"Disk-only top-level keys: <a>, <b>."`` when ``disk_only_top_level_keys``
    is a non-empty list with at least one usable string entry (deduped + sorted).
    Returns ``None`` for non-mapping ``diff``, ``error`` payloads, missing / non-list field,
    or empty after filtering.
    """
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    raw = diff.get("disk_only_top_level_keys")
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
    return "Disk-only top-level keys: " + ", ".join(sorted(cleaned)) + "."


def full_workflow_merge_paste_only_top_level_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    """One-line caption naming top-level keys in the paste but not on disk.

    Returns ``"Paste-only top-level keys: <a>, <b>."`` when ``paste_only_top_level_keys``
    is a non-empty list with at least one usable string entry (deduped + sorted).
    Returns ``None`` for non-mapping ``diff``, ``error`` payloads, missing / non-list field,
    or empty after filtering.
    """
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    raw = diff.get("paste_only_top_level_keys")
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
    return "Paste-only top-level keys: " + ", ".join(sorted(cleaned)) + "."


def full_workflow_merge_pasted_top_level_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    """One-line caption naming top-level keys present in the pasted YAML root."""
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    raw = diff.get("pasted_top_level_keys")
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
    return "Pasted top-level keys: " + ", ".join(sorted(cleaned)) + "."


def full_workflow_merge_added_top_level_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    """One-line caption naming the added top-level keys.

    Mirror of :func:`full_workflow_merge_changed_top_level_caption` for the
    ``added_top_level_keys`` field. Returns ``"Added top-level keys: <a>, <b>, <c>."``
    when the field is a non-empty list with at least one usable string entry.
    Entries are whitespace-stripped, empty / non-string entries are skipped, and
    surviving entries are deduped + sorted alphabetically before joining.

    Returns ``None`` for:

    * non-mapping ``diff`` or ``error`` payloads,
    * missing / non-list ``added_top_level_keys``,
    * an empty list, or
    * a list whose only entries are non-string / whitespace-only.
    """
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    raw = diff.get("added_top_level_keys")
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
    return "Added top-level keys: " + ", ".join(sorted(cleaned)) + "."


def full_workflow_merge_changed_top_level_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    """One-line caption naming the changed top-level keys.

    Returns ``"Changed top-level keys: <a>, <b>, <c>."`` when ``changed_top_level_keys``
    is a non-empty list with at least one string entry. Entries are whitespace-stripped,
    empty / non-string entries are skipped, and the surviving entries are deduped +
    sorted alphabetically before joining.

    Returns ``None`` for:

    * non-mapping ``diff`` or ``error`` payloads,
    * missing / non-list ``changed_top_level_keys``,
    * an empty list, or
    * a list whose only entries are non-string / whitespace-only (nothing left to
      surface after filtering).
    """
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    raw = diff.get("changed_top_level_keys")
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
    return "Changed top-level keys: " + ", ".join(sorted(cleaned)) + "."


def full_workflow_merge_unchanged_top_level_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    """Caption confirming a paste reproduces the on-disk workflow exactly.

    Returns ``"All top-level keys unchanged (<N> keys; paste reproduces disk)."`` when
    ``added_top_level_keys`` / ``removed_top_level_keys`` / ``changed_top_level_keys``
    are all empty lists (or absent / not a list, treated as ``0``) and
    ``unchanged_top_level_keys`` has at least one entry. Returns ``None`` when:

    * ``diff`` is not a mapping or carries an ``error`` payload,
    * any of the churn buckets is a non-empty list (real churn to surface), **or**
    * ``unchanged_top_level_keys`` is missing / empty (nothing to confirm).
    """
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None

    def _count(key: str) -> int:
        raw = diff.get(key)
        return len(raw) if isinstance(raw, list) else 0

    if _count("added_top_level_keys") > 0:
        return None
    if _count("removed_top_level_keys") > 0:
        return None
    if _count("changed_top_level_keys") > 0:
        return None
    unchanged_count = _count("unchanged_top_level_keys")
    if unchanged_count < 1:
        return None
    return (
        f"All top-level keys unchanged ({unchanged_count} keys; paste reproduces disk)."
    )


def full_workflow_merge_subtree_overview_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    """Compact subtree-level diff overview for the full-workflow dry-run.

    Aggregates ``subtree_field_diffs.{integrator_gate,agent_evaluator}.{added,removed,
    changed,unchanged}_keys`` list lengths (each treated as ``0`` when absent or not a
    list) into the single line::

        "Subtree churn: integrator_gate (+A / -R / ~C / =U), "
        "agent_evaluator (+A / -R / ~C / =U)"

    Subtree blocks that are missing or not a mapping contribute zero counts (so the
    caption is always two named blocks in the same fixed order as the existing subtree
    dataframe). Returns ``None`` when ``diff`` is not a mapping, carries an ``error``
    payload, or when ``subtree_field_diffs`` itself is missing / not a mapping (there is
    no subtree signal to summarise in that case).
    """
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    subtrees = diff.get("subtree_field_diffs")
    if not isinstance(subtrees, Mapping):
        return None

    def _count(block: Any, key: str) -> int:
        if not isinstance(block, Mapping):
            return 0
        raw = block.get(key)
        return len(raw) if isinstance(raw, list) else 0

    parts: list[str] = []
    for name in ("integrator_gate", "agent_evaluator"):
        block = subtrees.get(name)
        added = _count(block, "added_keys")
        removed = _count(block, "removed_keys")
        changed = _count(block, "changed_keys")
        unchanged = _count(block, "unchanged_keys")
        parts.append(f"{name} (+{added} / -{removed} / ~{changed} / ={unchanged})")
    return "Subtree churn: " + ", ".join(parts)


def full_workflow_merge_subtree_changed_fields_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    """One-line caption naming changed shallow keys under ``integrator_gate`` / ``agent_evaluator``.

    Complements :func:`full_workflow_merge_subtree_overview_caption` with concrete field
    names from ``subtree_field_diffs[*].changed_keys``. Per-block keys are whitespace-stripped,
    empty / non-string entries skipped, surviving entries deduped + sorted alphabetically,
    then capped at :data:`_SUBTREE_CHANGED_FIELDS_CAPTION_MAX_KEYS` with a trailing
    ``(+N more)`` overflow hint. A subtree block is **omitted** when ``changed_keys`` is
    missing, not a list, empty, or yields no usable strings after cleaning.

    Returns ``None`` when ``diff`` is not a mapping, carries an ``error`` payload, when
    ``subtree_field_diffs`` is missing / not a mapping, or when both subtrees have nothing
    to show.
    """
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
    """One-line caption naming removed shallow keys under ``integrator_gate`` / ``agent_evaluator``.

    Mirrors :func:`full_workflow_merge_subtree_changed_fields_caption` for
    ``subtree_field_diffs[*].removed_keys`` (same strip / dedupe / sort / cap rules).
    Returns ``None`` when there is nothing to show for either subtree or when the diff
    carries no usable ``subtree_field_diffs`` mapping.
    """
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
    """One-line caption naming added shallow keys under ``integrator_gate`` / ``agent_evaluator``.

    Mirrors :func:`full_workflow_merge_subtree_removed_fields_caption` for
    ``subtree_field_diffs[*].added_keys`` (same strip / dedupe / sort / cap rules).
    """
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


def full_workflow_merge_attention_rows(diff: Mapping[str, Any] | None) -> list[dict[str, str]]:
    """Read-only hints when a full-profile dry-run diff warrants extra operator review.

    Flags: removed top-level keys, **added** top-level keys, **disk-only** top-level keys
    (present on disk but absent from the pasted YAML — they survive shallow merge),
    **paste-only** top-level keys (present in the paste but absent from on-disk profile),
    **pasted** top-level keys (when ``pasted_top_level_keys`` is populated), simultaneous
    ``integrator_gate`` + ``agent_evaluator`` top-level changes, **removed shallow keys**
    under those subtrees (``subtree_field_diffs[*].removed_keys``), **added shallow keys**
    under those subtrees (``subtree_field_diffs[*].added_keys``), and **changed shallow
    keys** under those subtrees (``subtree_field_diffs[*].changed_keys``). Each per-name
    key list under the changed-keys flag is capped at the first
    :data:`_SUBTREE_CHANGED_KEYS_CAP` entries (``+N more`` hint appended on overflow).
    """
    if not isinstance(diff, Mapping) or diff.get("error"):
        return []
    rows: list[dict[str, str]] = []
    removed = diff.get("removed_top_level_keys")
    if isinstance(removed, list) and removed:
        rows.append(
            {
                "flag": "Removed top-level keys (paste omits these; they disappear on apply)",
                "keys": ", ".join(str(x) for x in removed),
            },
        )
    added = diff.get("added_top_level_keys")
    if isinstance(added, list) and added:
        rows.append(
            {
                "flag": "Added top-level keys (paste introduces new YAML sections on disk)",
                "keys": ", ".join(str(x) for x in sorted(added)),
            },
        )
    disk_only = diff.get("disk_only_top_level_keys")
    if isinstance(disk_only, list) and disk_only:
        rows.append(
            {
                "flag": (
                    "Disk-only top-level keys (not in pasted YAML; unchanged on disk after "
                    "shallow merge)"
                ),
                "keys": ", ".join(str(x) for x in disk_only),
            },
        )
    paste_only = diff.get("paste_only_top_level_keys")
    if isinstance(paste_only, list) and paste_only:
        rows.append(
            {
                "flag": (
                    "Paste-only top-level keys (in pasted YAML but not on disk; new sections "
                    "after shallow merge)"
                ),
                "keys": ", ".join(str(x) for x in paste_only),
            },
        )
    pasted_keys = diff.get("pasted_top_level_keys")
    if isinstance(pasted_keys, list) and pasted_keys:
        rows.append(
            {
                "flag": (
                    "Pasted top-level keys (YAML root keys in this paste; compare with "
                    "disk-only / added / removed hints above)"
                ),
                "keys": ", ".join(str(x) for x in pasted_keys),
            },
        )
    changed = diff.get("changed_top_level_keys")
    if (
        isinstance(changed, list)
        and "integrator_gate" in changed
        and "agent_evaluator" in changed
    ):
        rows.append(
            {
                "flag": "Both integrator_gate and agent_evaluator change in one paste",
                "keys": "Review subtree field tables and raw JSON before apply.",
            },
        )
    subtrees = diff.get("subtree_field_diffs")
    if isinstance(subtrees, dict):
        removed_parts: list[str] = []
        added_parts: list[str] = []
        changed_parts: list[str] = []
        for name in ("integrator_gate", "agent_evaluator"):
            inner = subtrees.get(name)
            if not isinstance(inner, dict):
                continue
            removed = inner.get("removed_keys")
            if isinstance(removed, list) and removed:
                removed_parts.append(
                    f"{name}: removed {', '.join(str(x) for x in removed)}",
                )
            added_inner = inner.get("added_keys")
            if isinstance(added_inner, list) and added_inner:
                added_parts.append(
                    f"{name}: added {', '.join(str(x) for x in added_inner)}",
                )
            changed_inner = inner.get("changed_keys")
            if isinstance(changed_inner, list) and changed_inner:
                visible = [str(x) for x in changed_inner[:_SUBTREE_CHANGED_KEYS_CAP]]
                overflow = len(changed_inner) - len(visible)
                tail = f" (+{overflow} more)" if overflow > 0 else ""
                changed_parts.append(
                    f"{name}: changed {', '.join(visible)}{tail}",
                )
        if removed_parts:
            rows.append(
                {
                    "flag": (
                        "Removed shallow keys under integrator_gate / agent_evaluator "
                        "(paste drops those YAML fields on apply)"
                    ),
                    "keys": "; ".join(removed_parts),
                },
            )
        if added_parts:
            rows.append(
                {
                    "flag": (
                        "Added shallow keys under integrator_gate / agent_evaluator "
                        "(paste introduces new YAML fields under those subtrees on apply)"
                    ),
                    "keys": "; ".join(added_parts),
                },
            )
        if changed_parts:
            rows.append(
                {
                    "flag": (
                        "Changed shallow keys under integrator_gate / agent_evaluator "
                        "(paste alters existing YAML values under those subtrees on apply)"
                    ),
                    "keys": "; ".join(changed_parts),
                },
            )
    return rows


def preview_effective_min_score_to_pass(
    repo_root: Path,
    workflow_profile: str | None,
    pasted_block: dict[str, Any] | None,
) -> float:
    """Resolve min score: env beats pasted ``min_score_to_pass``, then workflow file, then YAML."""
    env_raw = os.environ.get("HERMES_INTEGRATOR_MIN_SCORE_TO_PASS", "").strip()
    if env_raw:
        try:
            return max(0.0, min(1.0, float(env_raw)))
        except ValueError:
            pass
    if pasted_block:
        raw = pasted_block.get("min_score_to_pass")
        if raw is not None:
            try:
                return max(0.0, min(1.0, float(raw)))
            except (TypeError, ValueError):
                pass
    wf = parse_integrator_gate_min_score_to_pass(repo_root, workflow_profile)
    if wf is not None:
        return wf
    thr = repo_root / "configs" / "integrator" / "thresholds.yaml"
    if thr.is_file():
        return ModuleIntegrator.from_yaml(thr).min_score_to_pass
    return 0.0


def parse_synthetic_tags_json(text: str) -> tuple[list[str] | None, list[str]]:
    """Parse JSON array of tags; empty input → ``([], [])``."""
    raw = text.strip()
    if not raw:
        return [], []
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, [f"tags JSON: {exc}"]
    if not isinstance(obj, list):
        return None, ["tags JSON must be an array of strings"]
    out: list[str] = []
    for x in obj:
        if isinstance(x, str) and x.strip():
            out.append(x.strip())
        elif x is not None and not isinstance(x, str):
            return None, ["tags JSON must contain only strings"]
    return out, []


def build_project_profile_for_preview(
    repo_root: Path,
    *,
    workflow_profile: str | None,
    pasted_gate: dict[str, Any] | None,
    bundle_id: str,
    synthetic_tags: list[str] | None,
) -> dict[str, Any]:
    """Shape passed to :meth:`ModuleIntegrator.score_fit` (``tags`` + ``bundle_tags``)."""
    tags: list[str] = []
    if synthetic_tags:
        tags = list(synthetic_tags)
    elif pasted_gate and isinstance(pasted_gate.get("project_tags"), list):
        tags = [str(t).strip() for t in pasted_gate["project_tags"] if str(t).strip()]
    else:
        wf_pt = parse_integrator_gate_project_tags(repo_root, workflow_profile)
        if wf_pt is not None:
            tags = list(wf_pt)
    bid = str(bundle_id).strip() or "auth-rbac-starter"
    bundle_tags = load_bundle_tags_for_bundle_id(repo_root, bid)
    return {"tags": tags, "bundle_tags": bundle_tags}


def integrator_preview_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
    pasted_yaml: str,
    bundle_id: str,
    synthetic_tags_json: str,
) -> dict[str, Any]:
    """Single JSON-serializable dict for Streamlit tables / ``st.json``."""
    pasted_block, frag_errs = parse_integrator_gate_yaml_fragment(pasted_yaml)
    val_errs = validate_integrator_gate_block(pasted_block)
    tag_list, tag_errs = parse_synthetic_tags_json(synthetic_tags_json)
    all_errs = list(frag_errs) + val_errs + tag_errs

    wf_key = str(workflow_profile).strip() if workflow_profile else ""
    wf_sel = wf_key if wf_key else None

    disk_enabled = integrator_gate_workflow_enabled(repo_root, wf_sel)
    catalog_emit_enabled = load_integrator_gate_emit_enabled(repo_root)
    eff_min = preview_effective_min_score_to_pass(repo_root, wf_sel, pasted_block)
    integrator = ModuleIntegrator(min_score_to_pass=eff_min)

    bid = str(bundle_id).strip() or "auth-rbac-starter"
    profile = build_project_profile_for_preview(
        repo_root,
        workflow_profile=wf_sel,
        pasted_gate=pasted_block,
        bundle_id=bid,
        synthetic_tags=tag_list if tag_list is not None else [],
    )
    score = integrator.score_fit(bid, profile)
    passes = integrator.passes_gate(bid, profile)

    pasted_enabled: bool | None = None
    if pasted_block is not None and "enabled" in pasted_block:
        pasted_enabled = bool(pasted_block.get("enabled"))

    return {
        "workflow_profile": wf_sel,
        "disk_integrator_gate_enabled": disk_enabled,
        "catalog_thresholds_enabled": catalog_emit_enabled,
        "pasted_integrator_gate": pasted_block,
        "pasted_enabled_preview": pasted_enabled,
        "effective_min_score_to_pass": eff_min,
        "bundle_id": bid,
        "project_profile": profile,
        "score_fit": score,
        "passes_gate": passes,
        "validation_errors": all_errs,
    }


def full_workflow_merge_diff_export_filename_slug() -> str:
    """Filename slug prefix for full-workflow merge diff exports."""
    return "full_workflow_merge_diff"


_FULL_WORKFLOW_MERGE_DIFF_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def _full_workflow_merge_diff_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def full_workflow_merge_diff_table_rows(
    diff: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Sorted field/value rows for full-workflow merge diff export."""
    if not isinstance(diff, Mapping):
        return []
    if diff.get("error"):
        return []
    rows: list[dict[str, str]] = []
    for key in sorted(str(k) for k in diff.keys()):
        rows.append(
            {
                "field": key,
                "value": _full_workflow_merge_diff_cell(diff.get(key)),
            },
        )
    return rows


def full_workflow_merge_diff_export_json(
    diff: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for full-workflow merge diff payload."""
    if not isinstance(diff, Mapping):
        return "{}"
    return json.dumps(dict(diff), indent=2, ensure_ascii=False)


def full_workflow_merge_diff_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize full-workflow merge diff field/value rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_FULL_WORKFLOW_MERGE_DIFF_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _FULL_WORKFLOW_MERGE_DIFF_CSV_COLUMNS},
            )
    return buf.getvalue()


def _full_workflow_merge_diff_list_count(diff: Mapping[str, Any], key: str) -> int:
    raw = diff.get(key)
    return len(raw) if isinstance(raw, list) else 0


def full_workflow_merge_diff_operator_metrics(
    diff: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Structured rollup over :func:`full_workflow_merge_diff` output (§14 #13)."""
    metrics: dict[str, Any] = {
        "added_top_level_count": 0,
        "removed_top_level_count": 0,
        "changed_top_level_count": 0,
        "unchanged_top_level_count": 0,
        "top_level_churn": 0,
        "subtree_diff_count": 0,
        "paste_only_top_level_count": 0,
        "disk_only_top_level_count": 0,
        "has_error": False,
    }
    if not isinstance(diff, Mapping):
        return metrics
    if diff.get("error"):
        metrics["has_error"] = True
        return metrics
    added = _full_workflow_merge_diff_list_count(diff, "added_top_level_keys")
    removed = _full_workflow_merge_diff_list_count(diff, "removed_top_level_keys")
    changed = _full_workflow_merge_diff_list_count(diff, "changed_top_level_keys")
    unchanged = _full_workflow_merge_diff_list_count(diff, "unchanged_top_level_keys")
    metrics["added_top_level_count"] = added
    metrics["removed_top_level_count"] = removed
    metrics["changed_top_level_count"] = changed
    metrics["unchanged_top_level_count"] = unchanged
    metrics["top_level_churn"] = added + removed + changed
    subtrees = diff.get("subtree_field_diffs")
    if isinstance(subtrees, dict):
        metrics["subtree_diff_count"] = len(subtrees)
    paste_only = diff.get("paste_only_top_level_keys")
    if isinstance(paste_only, list):
        metrics["paste_only_top_level_count"] = len(paste_only)
    disk_only = diff.get("disk_only_top_level_keys")
    if isinstance(disk_only, list):
        metrics["disk_only_top_level_count"] = len(disk_only)
    return metrics


def full_workflow_merge_diff_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    if metrics.get("has_error") is True:
        return [{"field": "Error", "value": "yes"}]
    return [
        {"field": "Added top-level", "value": str(metrics.get("added_top_level_count", 0))},
        {"field": "Removed top-level", "value": str(metrics.get("removed_top_level_count", 0))},
        {"field": "Changed top-level", "value": str(metrics.get("changed_top_level_count", 0))},
        {
            "field": "Unchanged top-level",
            "value": str(metrics.get("unchanged_top_level_count", 0)),
        },
        {"field": "Top-level churn", "value": str(metrics.get("top_level_churn", 0))},
        {"field": "Subtree diffs", "value": str(metrics.get("subtree_diff_count", 0))},
        {
            "field": "Paste-only top-level",
            "value": str(metrics.get("paste_only_top_level_count", 0)),
        },
        {
            "field": "Disk-only top-level",
            "value": str(metrics.get("disk_only_top_level_count", 0)),
        },
    ]


def full_workflow_merge_diff_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line top-level diff overview from merge-diff operator metrics."""
    if not isinstance(metrics, Mapping) or metrics.get("has_error") is True:
        return None
    added = metrics.get("added_top_level_count", 0)
    removed = metrics.get("removed_top_level_count", 0)
    changed = metrics.get("changed_top_level_count", 0)
    unchanged = metrics.get("unchanged_top_level_count", 0)
    if not all(
        isinstance(x, int) and not isinstance(x, bool)
        for x in (added, removed, changed, unchanged)
    ):
        return None
    paste_only = metrics.get("paste_only_top_level_count", 0)
    disk_only = metrics.get("disk_only_top_level_count", 0)
    base = (
        f"Merge diff operator metrics: Top-level: +{added} / -{removed} / "
        f"~{changed} / ={unchanged}."
    )
    hints: list[str] = []
    if isinstance(paste_only, int) and not isinstance(paste_only, bool) and paste_only > 0:
        hints.append(f"**{paste_only}** paste-only key(s)")
    if isinstance(disk_only, int) and not isinstance(disk_only, bool) and disk_only > 0:
        hints.append(f"**{disk_only}** disk-only key(s)")
    if hints:
        return base[:-1] + "; " + ", ".join(hints) + "."
    return base


_FULL_WORKFLOW_MERGE_DIFF_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def full_workflow_merge_diff_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON export of :func:`full_workflow_merge_diff_operator_metrics`."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def full_workflow_merge_diff_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize full-workflow merge diff operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_FULL_WORKFLOW_MERGE_DIFF_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _FULL_WORKFLOW_MERGE_DIFF_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def full_workflow_merge_diff_operator_metrics_export_filename_slug() -> str:
    """Stable slug for full-workflow merge diff operator metrics downloads."""
    return "full_workflow_merge_diff_operator_metrics"


def full_workflow_merge_attention_export_filename_slug() -> str:
    """Filename slug prefix for full-workflow merge attention row exports."""
    return "full_workflow_merge_attention"


_FULL_WORKFLOW_MERGE_ATTENTION_CSV_COLUMNS: tuple[str, ...] = ("flag", "keys")


def full_workflow_merge_attention_export_json(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Pretty JSON for full-workflow merge attention hint rows."""
    out = [dict(r) for r in rows if isinstance(r, Mapping)]
    return json.dumps(out, indent=2, ensure_ascii=False)


def full_workflow_merge_attention_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize full-workflow merge attention rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_FULL_WORKFLOW_MERGE_ATTENTION_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _FULL_WORKFLOW_MERGE_ATTENTION_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def _full_workflow_merge_attention_subtree_row_count(diff: Mapping[str, Any]) -> int:
    """Count subtree removed/added/changed attention rows (mirrors attention_rows logic)."""
    subtrees = diff.get("subtree_field_diffs")
    if not isinstance(subtrees, dict):
        return 0
    removed_any = False
    added_any = False
    changed_any = False
    for name in ("integrator_gate", "agent_evaluator"):
        inner = subtrees.get(name)
        if not isinstance(inner, dict):
            continue
        if isinstance(inner.get("removed_keys"), list) and inner.get("removed_keys"):
            removed_any = True
        if isinstance(inner.get("added_keys"), list) and inner.get("added_keys"):
            added_any = True
        if isinstance(inner.get("changed_keys"), list) and inner.get("changed_keys"):
            changed_any = True
    return int(removed_any) + int(added_any) + int(changed_any)


def full_workflow_merge_attention_operator_metrics(
    diff: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Structured rollup over :func:`full_workflow_merge_attention_rows` (§14 #13)."""
    metrics: dict[str, Any] = {
        "attention_row_count": 0,
        "has_removed_top_level": False,
        "has_added_top_level": False,
        "has_disk_only_keys": False,
        "has_paste_only_keys": False,
        "has_dual_subtree_change": False,
        "subtree_attention_row_count": 0,
        "has_error": False,
    }
    if not isinstance(diff, Mapping):
        return metrics
    if diff.get("error"):
        metrics["has_error"] = True
        return metrics
    rows = full_workflow_merge_attention_rows(diff)
    metrics["attention_row_count"] = len(rows)
    removed = diff.get("removed_top_level_keys")
    metrics["has_removed_top_level"] = isinstance(removed, list) and bool(removed)
    added = diff.get("added_top_level_keys")
    metrics["has_added_top_level"] = isinstance(added, list) and bool(added)
    disk_only = diff.get("disk_only_top_level_keys")
    metrics["has_disk_only_keys"] = isinstance(disk_only, list) and bool(disk_only)
    paste_only = diff.get("paste_only_top_level_keys")
    metrics["has_paste_only_keys"] = isinstance(paste_only, list) and bool(paste_only)
    changed = diff.get("changed_top_level_keys")
    if isinstance(changed, list):
        metrics["has_dual_subtree_change"] = (
            "integrator_gate" in changed and "agent_evaluator" in changed
        )
    metrics["subtree_attention_row_count"] = _full_workflow_merge_attention_subtree_row_count(
        diff,
    )
    return metrics


def full_workflow_merge_attention_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    if metrics.get("has_error") is True:
        return [{"field": "Error", "value": "yes"}]
    return [
        {
            "field": "Attention row count",
            "value": str(metrics.get("attention_row_count", 0)),
        },
        {
            "field": "Removed top-level",
            "value": str(metrics.get("has_removed_top_level", False)).lower(),
        },
        {
            "field": "Added top-level",
            "value": str(metrics.get("has_added_top_level", False)).lower(),
        },
        {
            "field": "Disk-only keys",
            "value": str(metrics.get("has_disk_only_keys", False)).lower(),
        },
        {
            "field": "Paste-only keys",
            "value": str(metrics.get("has_paste_only_keys", False)).lower(),
        },
        {
            "field": "Dual subtree change",
            "value": str(metrics.get("has_dual_subtree_change", False)).lower(),
        },
        {
            "field": "Subtree attention rows",
            "value": str(metrics.get("subtree_attention_row_count", 0)),
        },
    ]


def full_workflow_merge_attention_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line caption when merge attention hints are present."""
    if not isinstance(metrics, Mapping) or metrics.get("has_error") is True:
        return None
    n = metrics.get("attention_row_count", 0)
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        return None
    word = "hint" if n == 1 else "hints"
    return f"Full-workflow merge attention metrics: **{n}** attention {word}."


_FULL_WORKFLOW_MERGE_ATTENTION_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def full_workflow_merge_attention_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON export of merge attention operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def full_workflow_merge_attention_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize merge attention operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_FULL_WORKFLOW_MERGE_ATTENTION_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _FULL_WORKFLOW_MERGE_ATTENTION_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def full_workflow_merge_attention_operator_metrics_export_filename_slug() -> str:
    """Stable slug for full-workflow merge attention operator metrics downloads."""
    return "full_workflow_merge_attention_operator_metrics"
