from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.mapping import field_error_text, load_error_text


def escalation_policy_yaml_verification_shape_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return None
    if field_error_text(payload, "escalation_policy_yaml_load_error") is not None:
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
    if load_error_text(payload) is not None:
        return None
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return None
    if field_error_text(payload, "escalation_policy_yaml_load_error") is not None:
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
    if field_error_text(payload, "escalation_policy_yaml_load_error") is not None:
        return None
    raw = payload.get("escalation_policy_yaml_anti_deadlock_min_progress_events")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    unit = "event" if raw == 1 else "events"
    return f"Escalation policy anti_deadlock.min_progress_events: **{raw}** {unit}."


def escalation_policy_yaml_anti_deadlock_shape_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return None
    if field_error_text(payload, "escalation_policy_yaml_load_error") is not None:
        return None
    has_ad = payload.get("escalation_policy_yaml_has_anti_deadlock_mapping")
    if has_ad is True:
        return (
            "Policy shape: top-level ``anti_deadlock`` mapping present (progress / deadlock knobs)."
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
    if load_error_text(payload) is not None:
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
    if load_error_text(payload) is not None:
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
    if field_error_text(payload, "escalation_policy_yaml_load_error") is not None:
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
    if field_error_text(payload, "escalation_policy_yaml_load_error") is not None:
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
    if field_error_text(payload, "escalation_policy_yaml_load_error") is not None:
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
    if field_error_text(payload, "escalation_policy_yaml_load_error") is not None:
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
    if field_error_text(payload, "escalation_policy_yaml_load_error") is not None:
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
    if field_error_text(payload, "escalation_policy_yaml_load_error") is not None:
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
    if field_error_text(payload, "escalation_policy_yaml_load_error") is not None:
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
    if field_error_text(payload, "escalation_policy_yaml_load_error") is not None:
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
        if field_error_text(payload, "escalation_policy_yaml_load_error") is not None:
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
