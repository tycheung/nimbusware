from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.field_caption import (
    escalation_policy_yaml_ready,
    payload_bool_shape_caption,
    payload_load_error_clear,
    payload_mapping,
    payload_nonempty_str_caption,
    payload_nonneg_int_caption,
)


def escalation_policy_yaml_verification_shape_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_bool_shape_caption(
        payload,
        "escalation_policy_yaml_has_verification_mapping",
        true_text=(
            "Policy shape: top-level ``verification`` mapping present "
            "(auto-escalate / threshold knobs)."
        ),
        false_text=(
            "Policy shape: no top-level ``verification`` mapping "
            "(unexpected vs standard agent ``policy.yaml``)."
        ),
        guard=escalation_policy_yaml_ready,
    )


def escalation_policy_yaml_deadlock_minutes_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonneg_int_caption(
        payload,
        "escalation_policy_yaml_deadlock_escalation_after_minutes",
        "Escalation policy deadlock_escalation_after_minutes: **{value}** {unit}.",
        guard=escalation_policy_yaml_ready,
        unit=lambda n: "minute" if n == 1 else "minutes",
    )


def escalation_policy_yaml_anti_deadlock_min_progress_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonneg_int_caption(
        payload,
        "escalation_policy_yaml_anti_deadlock_min_progress_events",
        "Escalation policy anti_deadlock.min_progress_events: **{value}** {unit}.",
        guard=escalation_policy_yaml_ready,
        unit=lambda n: "event" if n == 1 else "events",
    )


def escalation_policy_yaml_anti_deadlock_shape_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_bool_shape_caption(
        payload,
        "escalation_policy_yaml_has_anti_deadlock_mapping",
        true_text=(
            "Policy shape: top-level ``anti_deadlock`` mapping present (progress / deadlock knobs)."
        ),
        false_text=(
            "Policy shape: no top-level ``anti_deadlock`` mapping "
            "(unexpected vs standard agent ``policy.yaml``)."
        ),
        guard=escalation_policy_yaml_ready,
    )


def escalation_yaml_key_present_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    body = payload_load_error_clear(payload)
    if body is None:
        return None
    present = body.get("escalation_yaml_key_present")
    if present is not True:
        return "Escalation suppress: workflow YAML **escalation** key **absent**."
    effective = body.get("suppress_automatic_escalation_effective")
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
    body = payload_load_error_clear(payload)
    if body is None:
        return None
    effective = body.get("suppress_automatic_escalation_effective")
    if not isinstance(effective, bool):
        return None
    raw_type = body.get("suppress_automatic_escalation_yaml_raw_type")
    base = f"Suppress automatic escalation: {effective}"
    if isinstance(raw_type, str) and raw_type.strip():
        return f"{base} (YAML raw type: {raw_type.strip()})."
    return f"{base}."


def escalation_policy_yaml_age_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonneg_int_caption(
        payload,
        "escalation_policy_yaml_age_seconds",
        "Escalation policy YAML age: **{value}** seconds.",
        guard=escalation_policy_yaml_ready,
    )


def escalation_policy_yaml_file_bytes_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonneg_int_caption(
        payload,
        "escalation_policy_yaml_file_bytes",
        "Escalation policy YAML on disk: **{value}** bytes.",
        guard=escalation_policy_yaml_ready,
    )


def escalation_policy_yaml_key_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonneg_int_caption(
        payload,
        "escalation_policy_yaml_top_level_key_count",
        "Policy YAML top-level keys: {value}.",
        guard=escalation_policy_yaml_ready,
    )


def escalation_policy_yaml_version_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonneg_int_caption(
        payload,
        "escalation_policy_yaml_version",
        "Escalation policy YAML version: **{value}**.",
        guard=escalation_policy_yaml_ready,
        min_value=1,
    )


def escalation_policy_yaml_max_retries_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonneg_int_caption(
        payload,
        "escalation_policy_yaml_max_retries_per_stage",
        "Escalation policy max retries per stage: **{value}**.",
        guard=escalation_policy_yaml_ready,
    )


def escalation_policy_yaml_keys_sample_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    body = escalation_policy_yaml_ready(payload)
    if body is None:
        return None
    raw = body.get("escalation_policy_yaml_top_level_keys_sample")
    if not isinstance(raw, list) or not raw:
        return None
    usable = [entry.strip() for entry in raw if isinstance(entry, str) and entry.strip()]
    if not usable:
        return None
    return "Policy YAML top-level keys (sample): " + ", ".join(usable) + "."


def escalation_policy_yaml_relpath_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonempty_str_caption(
        payload,
        "escalation_policy_yaml_relpath",
        "Policy YAML path: {value}.",
        guard=escalation_policy_yaml_ready,
    )


def escalation_policy_yaml_mtime_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    body = escalation_policy_yaml_ready(payload)
    if body is None:
        return None
    iso = body.get("escalation_policy_yaml_mtime_iso")
    if not isinstance(iso, str) or not iso.strip():
        return None
    age = body.get("escalation_policy_yaml_age_seconds")
    if isinstance(age, bool) or not isinstance(age, int):
        return None
    return f"Policy YAML last modified: {iso.strip()} ({age} seconds ago)."


def escalation_policy_yaml_top_level_kinds_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    body = payload_mapping(payload)
    if body is None:
        return None

    explicit_path = "escalation_policy_yaml_top_level_kinds" in body
    if explicit_path:
        body = escalation_policy_yaml_ready(body)
        if body is None:
            return None
        kinds = body.get("escalation_policy_yaml_top_level_kinds")
    else:
        kinds = body

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
