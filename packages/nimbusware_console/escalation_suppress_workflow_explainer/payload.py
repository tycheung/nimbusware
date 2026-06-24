from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nimbusware_config.workflow_read import (
    escalation_policy_breadth,
    load_yaml,
    parse_escalation_workflow_block,
)
from nimbusware_console.explainer_core.repo_yaml import (
    json_safe_yaml_fragment,
    mtime_iso_utc,
    relative_under,
)
from nimbusware_console.explainer_core.time import age_seconds_utc as _age_seconds_utc
from nimbusware_console.explainer_core.workflow_payload_header import workflow_payload_header
from nimbusware_console.explainer_core.workflow_profile import yaml_section


def escalation_suppress_workflow_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
) -> dict[str, Any]:
    snap, header = workflow_payload_header(repo_root, workflow_profile)
    wf_sel = snap.workflow_profile
    policy_breadth = escalation_policy_breadth(repo_root)
    escalation_key_present = "escalation" in snap.disk_doc
    escalation_yaml_value = snap.disk_doc.get("escalation") if escalation_key_present else None
    esc_section = yaml_section(snap.disk_doc, "escalation")
    suppress_yaml_raw = esc_section.get("suppress_automatic_escalation") if esc_section else None

    parsed = parse_escalation_workflow_block(
        repo_root,
        wf_sel,
        config_materializer=snap.materializer,
    )

    suppress_yaml_raw_type: str | None
    if suppress_yaml_raw is None:
        suppress_yaml_raw_type = None
    else:
        suppress_yaml_raw_type = type(suppress_yaml_raw).__name__

    policy_path = repo_root / "configs" / "escalation" / "policy.yaml"
    mat = snap.materializer
    escalation_policy_yaml_path_exists = False
    escalation_policy_yaml_relpath: str | None = None
    escalation_policy_yaml_file_bytes: int | None = None
    escalation_policy_yaml_mtime_iso: str | None = None
    escalation_policy_yaml_top_level_key_count = 0
    escalation_policy_yaml_top_level_keys: list[str] = []
    escalation_policy_yaml_top_level_keys_sample: list[str] = []
    escalation_policy_yaml_top_level_kinds: dict[str, int] = {
        "mapping": 0,
        "scalar": 0,
        "list": 0,
        "other": 0,
    }
    escalation_policy_yaml_load_error: str | None = None
    escalation_policy_yaml_has_verification_mapping: bool | None = None
    escalation_policy_yaml_has_anti_deadlock_mapping: bool | None = None
    escalation_policy_yaml_max_retries_per_stage: int | None = None
    escalation_policy_yaml_deadlock_escalation_after_minutes: int | None = None
    escalation_policy_yaml_version: int | None = None
    escalation_policy_yaml_anti_deadlock_enabled: bool | None = None
    escalation_policy_yaml_anti_deadlock_min_progress_events: int | None = None
    pol_doc: Any = None
    if mat is not None and getattr(mat, "use_db", False):
        try:
            raw_pol = mat.get_escalation_policy()
            pol_doc = raw_pol if isinstance(raw_pol, dict) else None
            escalation_policy_yaml_path_exists = pol_doc is not None
            if escalation_policy_yaml_path_exists:
                escalation_policy_yaml_relpath = "configs/escalation/policy.yaml"
        except (AttributeError, KeyError):
            escalation_policy_yaml_path_exists = False
    elif policy_path.is_file():
        escalation_policy_yaml_path_exists = True
        escalation_policy_yaml_relpath = relative_under(repo_root, policy_path)
        escalation_policy_yaml_mtime_iso = mtime_iso_utc(policy_path)
        try:
            escalation_policy_yaml_file_bytes = int(policy_path.stat().st_size)
        except OSError:
            escalation_policy_yaml_file_bytes = None
        try:
            pol_doc = load_yaml(policy_path)
        except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError) as err:
            escalation_policy_yaml_load_error = str(err)
    if isinstance(pol_doc, dict):
        escalation_policy_yaml_has_verification_mapping = isinstance(
            pol_doc.get("verification"),
            dict,
        )
        escalation_policy_yaml_has_anti_deadlock_mapping = isinstance(
            pol_doc.get("anti_deadlock"),
            dict,
        )
        keys = sorted(str(k) for k in pol_doc if isinstance(k, str))
        escalation_policy_yaml_top_level_key_count = len(keys)
        escalation_policy_yaml_top_level_keys = keys
        escalation_policy_yaml_top_level_keys_sample = keys[:12]
        for k in pol_doc:
            if not isinstance(k, str):
                continue
            v = pol_doc[k]
            if isinstance(v, dict):
                escalation_policy_yaml_top_level_kinds["mapping"] += 1
            elif isinstance(v, list):
                escalation_policy_yaml_top_level_kinds["list"] += 1
            elif v is None or isinstance(v, (bool, int, float, str)):
                escalation_policy_yaml_top_level_kinds["scalar"] += 1
            else:
                escalation_policy_yaml_top_level_kinds["other"] += 1
        raw_mr = pol_doc.get("max_retries_per_stage")
        if type(raw_mr) is int and not isinstance(raw_mr, bool):
            escalation_policy_yaml_max_retries_per_stage = raw_mr
        raw_dm = pol_doc.get("deadlock_escalation_after_minutes")
        if type(raw_dm) is int and not isinstance(raw_dm, bool):
            escalation_policy_yaml_deadlock_escalation_after_minutes = raw_dm
        raw_pv = pol_doc.get("version")
        if type(raw_pv) is int and not isinstance(raw_pv, bool):
            escalation_policy_yaml_version = raw_pv
        ad_blk = pol_doc.get("anti_deadlock")
        if isinstance(ad_blk, dict):
            ad_en = ad_blk.get("enabled")
            if isinstance(ad_en, bool):
                escalation_policy_yaml_anti_deadlock_enabled = ad_en
            raw_mpe = ad_blk.get("min_progress_events")
            if type(raw_mpe) is int and not isinstance(raw_mpe, bool):
                escalation_policy_yaml_anti_deadlock_min_progress_events = raw_mpe

    escalation_policy_yaml_age_seconds: int | None = None
    if escalation_policy_yaml_path_exists and escalation_policy_yaml_load_error is None:
        escalation_policy_yaml_age_seconds = _age_seconds_utc(
            escalation_policy_yaml_mtime_iso,
        )

    return {
        **header,
        "escalation_yaml_key_present": escalation_key_present,
        "escalation_yaml_value": json_safe_yaml_fragment(escalation_yaml_value),
        "suppress_automatic_escalation_yaml_raw": suppress_yaml_raw,
        "suppress_automatic_escalation_yaml_raw_type": suppress_yaml_raw_type,
        "suppress_automatic_escalation_effective": parsed.suppress_automatic_escalation,
        "escalation_policy_yaml_path_exists": escalation_policy_yaml_path_exists,
        "escalation_policy_yaml_relpath": escalation_policy_yaml_relpath,
        "escalation_policy_yaml_file_bytes": escalation_policy_yaml_file_bytes,
        "escalation_policy_yaml_mtime_iso": escalation_policy_yaml_mtime_iso,
        "escalation_policy_yaml_age_seconds": escalation_policy_yaml_age_seconds,
        "escalation_policy_yaml_top_level_key_count": escalation_policy_yaml_top_level_key_count,
        "escalation_policy_yaml_top_level_keys": escalation_policy_yaml_top_level_keys,
        "escalation_policy_yaml_top_level_keys_sample": (
            escalation_policy_yaml_top_level_keys_sample
        ),
        "escalation_policy_yaml_top_level_kinds": escalation_policy_yaml_top_level_kinds,
        "escalation_policy_yaml_load_error": escalation_policy_yaml_load_error,
        "escalation_policy_yaml_has_verification_mapping": (
            escalation_policy_yaml_has_verification_mapping
        ),
        "escalation_policy_yaml_has_anti_deadlock_mapping": (
            escalation_policy_yaml_has_anti_deadlock_mapping
        ),
        "escalation_policy_yaml_max_retries_per_stage": (
            escalation_policy_yaml_max_retries_per_stage
        ),
        "escalation_policy_yaml_deadlock_escalation_after_minutes": (
            escalation_policy_yaml_deadlock_escalation_after_minutes
        ),
        "escalation_policy_yaml_version": escalation_policy_yaml_version,
        "escalation_policy_yaml_anti_deadlock_enabled": (
            escalation_policy_yaml_anti_deadlock_enabled
        ),
        "escalation_policy_yaml_anti_deadlock_min_progress_events": (
            escalation_policy_yaml_anti_deadlock_min_progress_events
        ),
        "escalation_policy_active_verification_triggers": policy_breadth.get(
            "active_verification_triggers",
        ),
        "escalation_policy_breadth_anti_deadlock_enabled": policy_breadth.get(
            "anti_deadlock_enabled",
        ),
    }
