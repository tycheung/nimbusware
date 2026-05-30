"""Apply workflow YAML edits: subtrees + full-profile merge.

Writes only when ``HERMES_ALLOW_WORKFLOW_YAML_WRITE`` is truthy and confirmation
matches the selected profile stem. Uses :func:`atomic_write_yaml` for a safe
replace on ``configs/workflows/{profile}.yaml``.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

from nimbusware_config.persist import (
    load_workflow_profile_dict,
    persist_workflow_profile_dict,
)
from nimbusware_console.integrator_workflow_preview import (
    parse_agent_evaluator_yaml_fragment,
    parse_full_workflow_yaml_paste,
    parse_integrator_gate_yaml_fragment,
    validate_agent_evaluator_block,
    validate_full_workflow_document,
    validate_integrator_gate_block,
)

ALLOW_WORKFLOW_YAML_WRITE_ENV = "HERMES_ALLOW_WORKFLOW_YAML_WRITE"


def _config_materializer(repo_root: Path) -> Any | None:
    from nimbusware_config import ConfigMaterializer, config_from_db_enabled

    if not config_from_db_enabled():
        return None
    if not os.environ.get("NIMBUSWARE_DATABASE_URL", "").strip():
        return None
    return ConfigMaterializer(repo_root)


def workflow_yaml_write_enabled() -> bool:
    """Truth gate for disk writes (``1`` / ``true`` / ``yes`` / ``on``, case-insensitive)."""
    raw = os.environ.get(ALLOW_WORKFLOW_YAML_WRITE_ENV, "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def merge_integrator_gate_into_profile_document(
    repo_root: Path,
    profile_stem: str,
    gate: dict[str, Any],
    *,
    materializer: Any | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
    """Return ``(merged_full_doc, before_integrator_gate, after_integrator_gate)``."""
    mat = materializer if materializer is not None else _config_materializer(repo_root)
    raw = load_workflow_profile_dict(repo_root, profile_stem, materializer=mat)
    merged = copy.deepcopy(raw)
    prev = merged.get("integrator_gate")
    before = dict(prev) if isinstance(prev, dict) else None
    merged["integrator_gate"] = dict(gate)
    return merged, before, dict(gate)


def normalize_agent_evaluator_block(block: dict[str, Any]) -> dict[str, Any]:
    """Coerce to the shape :func:`parse_agent_evaluator_workflow_block` expects after load."""
    enabled = bool(block.get("enabled", False))
    raw_pid = block.get("persona_id", "default")
    if raw_pid is None:
        persona_id = "default"
    else:
        persona_id = str(raw_pid).strip() or "default"
    auto_promote = bool(block.get("auto_promote_probation", False))
    ac_out: dict[str, Any] = {"enabled": False, "shelf": "", "display_name": ""}
    ac_raw = block.get("auto_create_persona")
    if isinstance(ac_raw, dict):
        ac_out["enabled"] = bool(ac_raw.get("enabled", False))
        s = ac_raw.get("shelf")
        ac_out["shelf"] = str(s).strip() if s is not None else ""
        dn = ac_raw.get("display_name")
        ac_out["display_name"] = str(dn).strip() if dn is not None else ""
    return {
        "enabled": enabled,
        "persona_id": persona_id,
        "auto_promote_probation": auto_promote,
        "auto_create_persona": ac_out,
    }


def merge_agent_evaluator_into_profile_document(
    repo_root: Path,
    profile_stem: str,
    agent_evaluator: dict[str, Any],
    *,
    materializer: Any | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
    """Return ``(merged_full_doc, before_agent_evaluator, after_agent_evaluator)``."""
    mat = materializer if materializer is not None else _config_materializer(repo_root)
    raw = load_workflow_profile_dict(repo_root, profile_stem, materializer=mat)
    merged = copy.deepcopy(raw)
    prev = merged.get("agent_evaluator")
    before = dict(prev) if isinstance(prev, dict) else None
    normalized = normalize_agent_evaluator_block(agent_evaluator)
    merged["agent_evaluator"] = dict(normalized)
    return merged, before, dict(normalized)


def merge_full_workflow_into_profile_document(
    repo_root: Path,
    profile_stem: str,
    pasted_root: dict[str, Any],
    *,
    materializer: Any | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Shallow-merge pasted keys over on-disk profile.

    Returns ``(merged, before_disk)``.
    """
    mat = materializer if materializer is not None else _config_materializer(repo_root)
    disk = load_workflow_profile_dict(repo_root, profile_stem, materializer=mat)
    if not isinstance(disk, dict):
        msg = f"workflow profile {profile_stem!r} root must be a mapping"
        raise ValueError(msg)
    before = copy.deepcopy(disk)
    merged = copy.deepcopy(disk)
    for k, v in pasted_root.items():
        merged[k] = copy.deepcopy(v)
    if isinstance(merged.get("agent_evaluator"), dict):
        merged["agent_evaluator"] = normalize_agent_evaluator_block(merged["agent_evaluator"])
    return merged, before


def prepare_full_workflow_apply(
    repo_root: Path,
    *,
    profile_stem: str,
    pasted_yaml: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    """Parse, validate, and merge a full workflow document without writing.

    Returns ``(merged_full, before_disk, errors)``. On error, ``merged_full`` is ``None``.
    """
    stem = str(profile_stem).strip()
    if not stem:
        return None, None, ["workflow profile stem is empty"]
    pasted, p_errs = parse_full_workflow_yaml_paste(pasted_yaml)
    errs = list(p_errs)
    if pasted is None:
        return None, None, errs or ["could not parse workflow YAML"]
    errs.extend(validate_full_workflow_document(pasted))
    if errs:
        return None, None, errs
    try:
        merged, before = merge_full_workflow_into_profile_document(repo_root, stem, pasted)
    except (FileNotFoundError, OSError, ValueError) as exc:
        return None, None, [str(exc)]
    return merged, before, []


def apply_full_workflow_yaml(
    repo_root: Path,
    *,
    profile_stem: str,
    pasted_yaml: str,
    confirm_profile_stem: str,
) -> tuple[bool, dict[str, Any] | None, list[str]]:
    """Write merged full workflow when guards pass."""
    if not workflow_yaml_write_enabled():
        return False, None, [
            f"Set {ALLOW_WORKFLOW_YAML_WRITE_ENV}=1 (or true/yes/on) to allow "
            "workflow YAML writes.",
        ]
    stem = str(profile_stem).strip()
    if stem != str(confirm_profile_stem).strip():
        return False, None, ["confirmation text must exactly match the selected profile stem."]
    merged, _before, prep_errs = prepare_full_workflow_apply(
        repo_root,
        profile_stem=stem,
        pasted_yaml=pasted_yaml,
    )
    if prep_errs or merged is None:
        return False, None, prep_errs
    mat = _config_materializer(repo_root)
    persist_workflow_profile_dict(repo_root, stem, merged, materializer=mat)
    return True, merged, []


def prepare_integrator_gate_apply(
    repo_root: Path,
    *,
    profile_stem: str,
    pasted_yaml: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    """Parse, validate, and merge without writing.

    Returns ``(merged_full, before_gate, after_gate, errors)``. On any error,
    ``merged_full`` is ``None``.
    """
    stem = str(profile_stem).strip()
    if not stem:
        return None, None, None, ["workflow profile stem is empty"]
    if not str(pasted_yaml).strip():
        return None, None, None, ["pasted YAML is empty"]
    block, frag_errs = parse_integrator_gate_yaml_fragment(pasted_yaml)
    errs = list(frag_errs)
    if block is None:
        if not errs:
            errs.append("could not parse integrator_gate from YAML")
        return None, None, None, errs
    errs.extend(validate_integrator_gate_block(block))
    if errs:
        return None, None, None, errs
    try:
        merged, before, after = merge_integrator_gate_into_profile_document(repo_root, stem, block)
    except (FileNotFoundError, OSError, ValueError) as exc:
        return None, None, None, [str(exc)]
    return merged, before, after, []


def prepare_agent_evaluator_apply(
    repo_root: Path,
    *,
    profile_stem: str,
    pasted_yaml: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    """Parse, validate, normalize, and merge ``agent_evaluator`` without writing."""
    stem = str(profile_stem).strip()
    if not stem:
        return None, None, None, ["workflow profile stem is empty"]
    if not str(pasted_yaml).strip():
        return None, None, None, ["pasted YAML is empty"]
    block, frag_errs = parse_agent_evaluator_yaml_fragment(pasted_yaml)
    errs = list(frag_errs)
    if block is None:
        if not errs:
            errs.append("could not parse agent_evaluator from YAML")
        return None, None, None, errs
    errs.extend(validate_agent_evaluator_block(block))
    if errs:
        return None, None, None, errs
    normalized = normalize_agent_evaluator_block(block)
    try:
        merged, before, after = merge_agent_evaluator_into_profile_document(
            repo_root,
            stem,
            normalized,
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        return None, None, None, [str(exc)]
    return merged, before, after, []


def apply_integrator_gate_yaml(
    repo_root: Path,
    *,
    profile_stem: str,
    pasted_yaml: str,
    confirm_profile_stem: str,
) -> tuple[bool, dict[str, Any] | None, list[str]]:
    """Write merged workflow YAML when guards pass. Returns ``(ok, merged_doc, errors)``."""
    if not workflow_yaml_write_enabled():
        return False, None, [
            f"Set {ALLOW_WORKFLOW_YAML_WRITE_ENV}=1 (or true/yes/on) to allow "
            "workflow YAML writes.",
        ]
    stem = str(profile_stem).strip()
    if stem != str(confirm_profile_stem).strip():
        return False, None, ["confirmation text must exactly match the selected profile stem."]
    merged, _before, _after, prep_errs = prepare_integrator_gate_apply(
        repo_root,
        profile_stem=stem,
        pasted_yaml=pasted_yaml,
    )
    if prep_errs or merged is None:
        return False, None, prep_errs
    mat = _config_materializer(repo_root)
    persist_workflow_profile_dict(repo_root, stem, merged, materializer=mat)
    return True, merged, []


def apply_agent_evaluator_yaml(
    repo_root: Path,
    *,
    profile_stem: str,
    pasted_yaml: str,
    confirm_profile_stem: str,
) -> tuple[bool, dict[str, Any] | None, list[str]]:
    """Write merged workflow YAML when guards pass (``agent_evaluator`` subtree only)."""
    if not workflow_yaml_write_enabled():
        return False, None, [
            f"Set {ALLOW_WORKFLOW_YAML_WRITE_ENV}=1 (or true/yes/on) to allow "
            "workflow YAML writes.",
        ]
    stem = str(profile_stem).strip()
    if stem != str(confirm_profile_stem).strip():
        return False, None, ["confirmation text must exactly match the selected profile stem."]
    merged, _before, _after, prep_errs = prepare_agent_evaluator_apply(
        repo_root,
        profile_stem=stem,
        pasted_yaml=pasted_yaml,
    )
    if prep_errs or merged is None:
        return False, None, prep_errs
    mat = _config_materializer(repo_root)
    persist_workflow_profile_dict(repo_root, stem, merged, materializer=mat)
    return True, merged, []
