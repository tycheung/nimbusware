from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from hermes_extensions.personas import ALLOWED_SHELVES

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


