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

from nimbusware_console.integrator_preview.merge import full_workflow_merge_diff
from nimbusware_console.integrator_preview.parse import (
    parse_integrator_gate_yaml_fragment,
    validate_full_workflow_document,
    validate_integrator_gate_block,
)
def preview_effective_min_score_to_pass(
    repo_root: Path,
    workflow_profile: str | None,
    pasted_block: dict[str, Any] | None,
) -> float:
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


