from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

import yaml

from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_workflow_disk import load_workflow_profile_documents
from hermes_orchestrator.merge import load_yaml
from hermes_orchestrator.workflow_escalation import parse_escalation_workflow_block
from hermes_orchestrator.workflow_profiles import workflow_profile_dict, workflow_profile_path


def _mtime_iso_utc(path: Path) -> str | None:
    try:
        mtime_ns = int(path.stat().st_mtime_ns)
    except OSError:
        return None
    return datetime.fromtimestamp(mtime_ns / 1e9, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ",
    )


def _age_seconds_utc(iso: str | None) -> int | None:
    if not isinstance(iso, str):
        return None
    stripped = iso.strip()
    if not stripped:
        return None
    normalised = stripped[:-1] + "+00:00" if stripped.endswith("Z") else stripped
    try:
        parsed = datetime.fromisoformat(normalised)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    age = int((datetime.now(timezone.utc) - parsed).total_seconds())
    if age < 0:
        return None
    return age


def _relative_under(repo_root: Path, path: Path) -> str:
    root = repo_root.resolve()
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path.resolve())


def _json_safe_yaml_fragment(raw: object) -> object:
    if raw is None or isinstance(raw, (bool, int, float, str)):
        return raw
    if isinstance(raw, dict):
        out: dict[str, Any] = {}
        for k, v in raw.items():
            sk = k if isinstance(k, str) else str(k)
            out[sk] = _json_safe_yaml_fragment(v)
        return out
    if isinstance(raw, list):
        return [_json_safe_yaml_fragment(x) for x in raw]
    return str(raw)


def escalation_suppress_workflow_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
) -> dict[str, Any]:
    wf_key = str(workflow_profile).strip() if workflow_profile else ""
    wf_sel: str | None = wf_key if wf_key else None

    mat = console_config_materializer(repo_root)
    from hermes_orchestrator.escalation_policy_breadth import escalation_policy_breadth

    policy_breadth = escalation_policy_breadth(repo_root)

    workflow_yaml_relpath: str | None = None
    load_error: str | None = None
    workflow_yaml_top_level_version_int: int | None = None
    escalation_key_present = False
    escalation_yaml_value: Any = None
    suppress_yaml_raw: Any = None

    if wf_sel:
        try:
            disk_doc, _effective_doc, wp, _file_bytes = load_workflow_profile_documents(
                repo_root,
                wf_sel,
                materializer=mat,
            )
            workflow_yaml_relpath = _relative_under(repo_root, wp)
            doc = disk_doc
            if isinstance(doc, dict):
                vtop = doc.get("version")
                if type(vtop) is int and not isinstance(vtop, bool):
                    workflow_yaml_top_level_version_int = vtop
            if isinstance(doc, dict) and "escalation" in doc:
                escalation_key_present = True
                escalation_yaml_value = doc.get("escalation")
                if isinstance(escalation_yaml_value, dict):
                    suppress_yaml_raw = escalation_yaml_value.get(
                        "suppress_automatic_escalation",
                    )
        except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError) as err:
            load_error = str(err)
            escalation_yaml_value = None

    parsed = parse_escalation_workflow_block(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )

    suppress_yaml_raw_type: str | None
    if suppress_yaml_raw is None:
        suppress_yaml_raw_type = None
    else:
        suppress_yaml_raw_type = type(suppress_yaml_raw).__name__

    policy_path = repo_root / "configs" / "escalation" / "policy.yaml"
    escalation_policy_yaml_path_exists = policy_path.is_file()
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
    if escalation_policy_yaml_path_exists:
        escalation_policy_yaml_relpath = _relative_under(repo_root, policy_path)
        escalation_policy_yaml_mtime_iso = _mtime_iso_utc(policy_path)
        try:
            escalation_policy_yaml_file_bytes = int(policy_path.stat().st_size)
        except OSError:
            escalation_policy_yaml_file_bytes = None
        pol_doc: Any = None
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
    if (
        escalation_policy_yaml_path_exists
        and escalation_policy_yaml_load_error is None
    ):
        escalation_policy_yaml_age_seconds = _age_seconds_utc(
            escalation_policy_yaml_mtime_iso,
        )

    return {
        "workflow_profile": wf_sel,
        "workflow_yaml_relpath": workflow_yaml_relpath,
        "workflow_yaml_top_level_version_int": workflow_yaml_top_level_version_int,
        "escalation_yaml_key_present": escalation_key_present,
        "escalation_yaml_value": _json_safe_yaml_fragment(escalation_yaml_value),
        "suppress_automatic_escalation_yaml_raw": suppress_yaml_raw,
        "suppress_automatic_escalation_yaml_raw_type": suppress_yaml_raw_type,
        "suppress_automatic_escalation_effective": parsed.suppress_automatic_escalation,
        "load_error": load_error,
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


def escalation_policy_yaml_verification_shape_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return None
    pol_err = payload.get("escalation_policy_yaml_load_error")
    if isinstance(pol_err, str) and pol_err.strip():
        return None
    has_v = payload.get("escalation_policy_yaml_has_verification_mapping")
    if has_v is True:
        return (
            "Policy shape: top-level ``verification`` mapping present "
            "(auto-escalate / threshold knobs)."
        )
    if has_v is False:
        return (
            "Policy shape: no top-level ``verification`` mapping "
            "(unexpected vs standard agent ``policy.yaml``)."
        )
    return None


def escalation_policy_yaml_deadlock_minutes_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return None
    pol_err = payload.get("escalation_policy_yaml_load_error")
    if isinstance(pol_err, str) and pol_err.strip():
        return None
    raw = payload.get("escalation_policy_yaml_deadlock_escalation_after_minutes")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    unit = "minute" if raw == 1 else "minutes"
    return f"Escalation policy deadlock_escalation_after_minutes: **{raw}** {unit}."


def escalation_policy_yaml_anti_deadlock_min_progress_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return None
    pol_err = payload.get("escalation_policy_yaml_load_error")
    if isinstance(pol_err, str) and pol_err.strip():
        return None
    raw = payload.get("escalation_policy_yaml_anti_deadlock_min_progress_events")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    unit = "event" if raw == 1 else "events"
    return (
        f"Escalation policy anti_deadlock.min_progress_events: **{raw}** {unit}."
    )


def escalation_policy_yaml_anti_deadlock_shape_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return None
    pol_err = payload.get("escalation_policy_yaml_load_error")
    if isinstance(pol_err, str) and pol_err.strip():
        return None
    has_ad = payload.get("escalation_policy_yaml_has_anti_deadlock_mapping")
    if has_ad is True:
        return (
            "Policy shape: top-level ``anti_deadlock`` mapping present "
            "(progress / deadlock knobs)."
        )
    if has_ad is False:
        return (
            "Policy shape: no top-level ``anti_deadlock`` mapping "
            "(unexpected vs standard agent ``policy.yaml``)."
        )
    return None


def escalation_yaml_key_present_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_err = payload.get("load_error")
    if isinstance(load_err, str) and load_err.strip():
        return None
    present = payload.get("escalation_yaml_key_present")
    if present is not True:
        return "Escalation suppress: workflow YAML **escalation** key **absent**."
    effective = payload.get("suppress_automatic_escalation_effective")
    if effective is True:
        return (
            "Escalation suppress: workflow **escalation** key **present**, "
            "suppress_automatic_escalation=**true**."
        )
    if effective is False:
        return (
            "Escalation suppress: workflow **escalation** key **present**, "
            "suppress_automatic_escalation=**false**."
        )
    return (
        "Escalation suppress: workflow **escalation** key **present** "
        "(effective suppress flag not observable)."
    )


def escalation_suppress_flag_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_err = payload.get("load_error")
    if isinstance(load_err, str) and load_err.strip():
        return None
    effective = payload.get("suppress_automatic_escalation_effective")
    if not isinstance(effective, bool):
        return None
    raw_type = payload.get("suppress_automatic_escalation_yaml_raw_type")
    base = f"Suppress automatic escalation: {effective}"
    if isinstance(raw_type, str) and raw_type.strip():
        return f"{base} (YAML raw type: {raw_type.strip()})."
    return f"{base}."


def escalation_policy_yaml_age_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_err = payload.get("escalation_policy_yaml_load_error")
    if isinstance(load_err, str) and load_err.strip():
        return None
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return None
    raw = payload.get("escalation_policy_yaml_age_seconds")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Escalation policy YAML age: **{raw}** seconds."


def escalation_policy_yaml_file_bytes_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_err = payload.get("escalation_policy_yaml_load_error")
    if isinstance(load_err, str) and load_err.strip():
        return None
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return None
    raw = payload.get("escalation_policy_yaml_file_bytes")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Escalation policy YAML on disk: **{raw}** bytes."


def escalation_policy_yaml_key_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_err = payload.get("escalation_policy_yaml_load_error")
    if isinstance(load_err, str) and load_err.strip():
        return None
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return None
    raw = payload.get("escalation_policy_yaml_top_level_key_count")
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    if raw < 0:
        return None
    return f"Policy YAML top-level keys: {raw}."


def escalation_policy_yaml_version_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_err = payload.get("escalation_policy_yaml_load_error")
    if isinstance(load_err, str) and load_err.strip():
        return None
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return None
    ver = payload.get("escalation_policy_yaml_version")
    if not isinstance(ver, int) or isinstance(ver, bool) or ver < 1:
        return None
    return f"Escalation policy YAML version: **{ver}**."


def escalation_policy_yaml_max_retries_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_err = payload.get("escalation_policy_yaml_load_error")
    if isinstance(load_err, str) and load_err.strip():
        return None
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return None
    raw = payload.get("escalation_policy_yaml_max_retries_per_stage")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Escalation policy max retries per stage: **{raw}**."


def escalation_policy_yaml_keys_sample_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_err = payload.get("escalation_policy_yaml_load_error")
    if isinstance(load_err, str) and load_err.strip():
        return None
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return None
    raw = payload.get("escalation_policy_yaml_top_level_keys_sample")
    if not isinstance(raw, list) or not raw:
        return None
    usable: list[str] = []
    for entry in raw:
        if not isinstance(entry, str):
            continue
        trimmed = entry.strip()
        if trimmed:
            usable.append(trimmed)
    if not usable:
        return None
    return "Policy YAML top-level keys (sample): " + ", ".join(usable) + "."


def escalation_policy_yaml_relpath_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_err = payload.get("escalation_policy_yaml_load_error")
    if isinstance(load_err, str) and load_err.strip():
        return None
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return None
    rel = payload.get("escalation_policy_yaml_relpath")
    if not isinstance(rel, str):
        return None
    trimmed = rel.strip()
    if not trimmed:
        return None
    return f"Policy YAML path: {trimmed}."


def escalation_policy_yaml_mtime_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if not payload.get("escalation_policy_yaml_path_exists", True):
        return None
    load_err = payload.get("escalation_policy_yaml_load_error")
    if isinstance(load_err, str) and load_err.strip():
        return None
    iso = payload.get("escalation_policy_yaml_mtime_iso")
    if not isinstance(iso, str) or not iso.strip():
        return None
    age = payload.get("escalation_policy_yaml_age_seconds")
    if isinstance(age, bool) or not isinstance(age, int):
        return None
    return f"Policy YAML last modified: {iso.strip()} ({age} seconds ago)."


def escalation_policy_yaml_top_level_kinds_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None

    explicit_path = "escalation_policy_yaml_top_level_kinds" in payload
    if explicit_path:
        if not payload.get("escalation_policy_yaml_path_exists", True):
            return None
        load_err = payload.get("escalation_policy_yaml_load_error")
        if isinstance(load_err, str) and load_err.strip():
            return None
        kinds = payload.get("escalation_policy_yaml_top_level_kinds")
    else:
        kinds = payload

    if not isinstance(kinds, Mapping):
        return None

    def _count(key: str) -> int:
        raw = kinds.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int):
            return 0
        return max(raw, 0)

    mapping_n = _count("mapping")
    scalar_n = _count("scalar")
    list_n = _count("list")
    other_n = _count("other")
    if (mapping_n + scalar_n + list_n + other_n) == 0:
        return None
    return (
        f"Policy top-level kinds: {mapping_n} mapping(s), "
        f"{scalar_n} scalar(s), {list_n} list(s), {other_n} other."
    )


def escalation_policy_export_filename_slug() -> str:
    return "escalation_policy"


def escalation_suppress_export_filename_slug() -> str:
    return "escalation_suppress"


_EXPLAINER_FIELD_VALUE_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def _escalation_suppress_explainer_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def escalation_suppress_explainer_table_rows(
    payload: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(payload, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key in sorted(str(k) for k in payload.keys()):
        rows.append(
            {
                "field": key,
                "value": _escalation_suppress_explainer_cell(payload.get(key)),
            },
        )
    return rows


def escalation_suppress_explainer_export_json(
    payload: Mapping[str, Any] | None,
) -> str:
    if not isinstance(payload, Mapping):
        return "{}"
    return json.dumps(dict(payload), indent=2, ensure_ascii=False)


def escalation_suppress_explainer_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_EXPLAINER_FIELD_VALUE_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _EXPLAINER_FIELD_VALUE_CSV_COLUMNS})
    return buf.getvalue()


_ESCALATION_SUPPRESS_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def escalation_suppress_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "escalation_key_present": False,
        "suppress_automatic_escalation_effective": False,
        "policy_yaml_exists": False,
        "policy_top_level_key_count": 0,
        "anti_deadlock_mapping_present": False,
        "anti_deadlock_enabled": False,
        "anti_deadlock_min_progress_events": None,
        "policy_yaml_file_bytes": None,
        "policy_yaml_age_seconds": None,
        "load_error_present": False,
    }
    if not isinstance(payload, Mapping):
        return metrics
    metrics["escalation_key_present"] = payload.get("escalation_yaml_key_present") is True
    metrics["suppress_automatic_escalation_effective"] = (
        payload.get("suppress_automatic_escalation_effective") is True
    )
    metrics["policy_yaml_exists"] = payload.get("escalation_policy_yaml_path_exists") is True
    raw_kc = payload.get("escalation_policy_yaml_top_level_key_count")
    if isinstance(raw_kc, int) and not isinstance(raw_kc, bool) and raw_kc >= 0:
        metrics["policy_top_level_key_count"] = raw_kc
    metrics["anti_deadlock_mapping_present"] = (
        payload.get("escalation_policy_yaml_has_anti_deadlock_mapping") is True
    )
    if payload.get("escalation_policy_yaml_anti_deadlock_enabled") is True:
        metrics["anti_deadlock_enabled"] = True
    raw_mp = payload.get("escalation_policy_yaml_anti_deadlock_min_progress_events")
    if isinstance(raw_mp, int) and not isinstance(raw_mp, bool) and raw_mp >= 0:
        metrics["anti_deadlock_min_progress_events"] = raw_mp
    raw_bytes = payload.get("escalation_policy_yaml_file_bytes")
    if isinstance(raw_bytes, int) and not isinstance(raw_bytes, bool) and raw_bytes >= 0:
        metrics["policy_yaml_file_bytes"] = raw_bytes
    age = payload.get("escalation_policy_yaml_age_seconds")
    if isinstance(age, int) and not isinstance(age, bool) and age >= 0:
        metrics["policy_yaml_age_seconds"] = age
    err = payload.get("load_error")
    metrics["load_error_present"] = isinstance(err, str) and bool(err.strip())
    return metrics


def escalation_suppress_workflow_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {
            "field": "Escalation key present",
            "value": str(metrics.get("escalation_key_present", False)).lower(),
        },
        {
            "field": "Suppress automatic (effective)",
            "value": str(
                metrics.get("suppress_automatic_escalation_effective", False),
            ).lower(),
        },
        {
            "field": "Policy YAML exists",
            "value": str(metrics.get("policy_yaml_exists", False)).lower(),
        },
        {
            "field": "Policy top-level keys",
            "value": str(metrics.get("policy_top_level_key_count", 0)),
        },
        {
            "field": "anti_deadlock mapping",
            "value": str(metrics.get("anti_deadlock_mapping_present", False)).lower(),
        },
        {
            "field": "anti_deadlock enabled",
            "value": str(metrics.get("anti_deadlock_enabled", False)).lower(),
        },
    ]
    mp = metrics.get("anti_deadlock_min_progress_events")
    if isinstance(mp, int) and not isinstance(mp, bool):
        rows.append(
            {"field": "anti_deadlock min_progress_events", "value": str(mp)},
        )
    raw_bytes = metrics.get("policy_yaml_file_bytes")
    if isinstance(raw_bytes, int) and not isinstance(raw_bytes, bool):
        rows.append({"field": "Policy YAML bytes", "value": str(raw_bytes)})
    age = metrics.get("policy_yaml_age_seconds")
    if isinstance(age, int) and not isinstance(age, bool):
        rows.append({"field": "Policy YAML age (s)", "value": str(age)})
    return rows


def escalation_suppress_workflow_explainer_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def escalation_suppress_workflow_explainer_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_ESCALATION_SUPPRESS_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _ESCALATION_SUPPRESS_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def escalation_suppress_workflow_explainer_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    parts: list[str] = []
    if metrics.get("suppress_automatic_escalation_effective") is True:
        parts.append("suppress automatic **on**")
    else:
        parts.append("suppress automatic **off**")
    if metrics.get("policy_yaml_exists") is True:
        parts.append("policy file present")
    else:
        parts.append("policy file missing")
    if metrics.get("anti_deadlock_mapping_present") is True:
        mp = metrics.get("anti_deadlock_min_progress_events")
        if isinstance(mp, int) and not isinstance(mp, bool):
            parts.append(f"anti_deadlock min_progress **{mp}**")
        elif metrics.get("anti_deadlock_enabled") is True:
            parts.append("anti_deadlock **enabled**")
    age = metrics.get("policy_yaml_age_seconds")
    if isinstance(age, int) and not isinstance(age, bool):
        parts.append(f"policy age **{age}s**")
    raw_bytes = metrics.get("policy_yaml_file_bytes")
    if isinstance(raw_bytes, int) and not isinstance(raw_bytes, bool) and raw_bytes > 0:
        parts.append(f"policy YAML **{raw_bytes}** byte(s)")
    if metrics.get("load_error_present") is True:
        parts.append("load error")
    return "Escalation suppress explainer metrics: " + ", ".join(parts) + "."


def escalation_suppress_workflow_explainer_operator_metrics_export_filename_slug() -> str:
    return "escalation_suppress_workflow_explainer_operator_metrics"


_POLICY_KEYS_CSV_COLUMNS: tuple[str, ...] = ("policy_key",)

_POLICY_KINDS_CSV_COLUMNS: tuple[str, ...] = ("kind", "count")

_POLICY_KINDS_ORDER: tuple[str, ...] = ("mapping", "scalar", "list", "other")


def _escalation_policy_keys_rows_from_list(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for key in raw:
        if isinstance(key, str) and key.strip():
            out.append({"policy_key": key.strip()})
    return out


def escalation_policy_yaml_keys_all_table_rows(
    payload: Mapping[str, Any],
) -> list[dict[str, str]]:
    if not isinstance(payload, Mapping):
        return []
    full = payload.get("escalation_policy_yaml_top_level_keys")
    if isinstance(full, list) and full:
        return _escalation_policy_keys_rows_from_list(full)
    return _escalation_policy_keys_rows_from_list(
        payload.get("escalation_policy_yaml_top_level_keys_sample"),
    )


def escalation_policy_yaml_keys_all_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


def escalation_policy_yaml_keys_all_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_POLICY_KEYS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _POLICY_KEYS_CSV_COLUMNS})
    return buf.getvalue()


def escalation_policy_yaml_top_level_kinds_table_rows(
    payload: Mapping[str, Any],
) -> list[dict[str, str]]:
    if not isinstance(payload, Mapping):
        return []
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return []
    load_err = payload.get("escalation_policy_yaml_load_error")
    if isinstance(load_err, str) and load_err.strip():
        return []
    kinds = payload.get("escalation_policy_yaml_top_level_kinds")
    if not isinstance(kinds, Mapping):
        return []

    def _count(key: str) -> int:
        raw = kinds.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int):
            return 0
        return max(raw, 0)

    mapping_n = _count("mapping")
    scalar_n = _count("scalar")
    list_n = _count("list")
    other_n = _count("other")
    if (mapping_n + scalar_n + list_n + other_n) == 0:
        return []
    return [
        {"kind": kind, "count": str(_count(kind))}
        for kind in _POLICY_KINDS_ORDER
    ]


def escalation_policy_yaml_top_level_kinds_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


def escalation_policy_yaml_top_level_kinds_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_POLICY_KINDS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _POLICY_KINDS_CSV_COLUMNS})
    return buf.getvalue()
