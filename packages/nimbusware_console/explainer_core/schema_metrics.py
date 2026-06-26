from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from agent_core.coercion import as_float, as_stripped_str, is_number, is_strict_int
from nimbusware_console.explainer_core.metrics_scaffold import (
    apply_bool_payload_fields,
    apply_env_flag_metric,
    apply_env_tri_state_metrics,
    apply_load_error_present,
    apply_nested_bool_fields,
    apply_nonneg_int_fields,
    apply_optional_int_field,
    apply_str_present,
    apply_workflow_yaml_file_metrics,
    default_operator_metrics,
)

EnvTriStateSpec = str | tuple[str, str, str, str]
EnvFlagSpec = tuple[str, str, str]
NestedFieldSpec = tuple[str, Sequence[tuple[str, str]]]
NestedOptionalInt = tuple[str, str, str]
OptionalIntSpec = tuple[str, str] | tuple[str, str, bool]
BoolMatchSpec = tuple[str, str, str]


def build_operator_metrics(
    payload: Mapping[str, Any] | None,
    defaults: Mapping[str, Any],
    *,
    bool_fields: Sequence[tuple[str, str]] = (),
    int_fields: Sequence[tuple[str, str]] = (),
    nested_bool_fields: Sequence[NestedFieldSpec] = (),
    nested_int_fields: Sequence[NestedFieldSpec] = (),
    nested_optional_int: Sequence[NestedOptionalInt] = (),
    nested_exists: Sequence[tuple[str, str]] = (),
    list_nonempty_flags: Sequence[tuple[str, str]] = (),
    float_fields: Sequence[tuple[str, str]] = (),
    list_len_fields: Sequence[tuple[str, str]] = (),
    bool_match_fields: Sequence[BoolMatchSpec] = (),
    str_present: Sequence[tuple[str, str]] = (),
    optional_int: Sequence[OptionalIntSpec] = (),
    env_tri_state: Sequence[EnvTriStateSpec] = (),
    env_flags: Sequence[EnvFlagSpec] = (),
    workflow_yaml_file: bool = False,
    load_error: bool = False,
    bool_value_fields: Sequence[tuple[str, str]] = (),
    str_strip_fields: Sequence[tuple[str, str]] = (),
    load_error_payload_key: str = "load_error",
    load_error_metric_key: str = "load_error_present",
) -> dict[str, Any]:
    metrics = default_operator_metrics(defaults)
    if not isinstance(payload, Mapping):
        return metrics
    if bool_fields:
        apply_bool_payload_fields(metrics, payload, bool_fields)
    for nested_key, fields in nested_bool_fields:
        apply_nested_bool_fields(metrics, payload, nested_key, fields)
    for nested_key, fields in nested_int_fields:
        nested = payload.get(nested_key)
        if isinstance(nested, Mapping):
            apply_nonneg_int_fields(metrics, nested, fields)
    for nested_key, field, metric_key in nested_optional_int:
        nested = payload.get(nested_key)
        if isinstance(nested, Mapping):
            apply_optional_int_field(metrics, nested, field, metric_key)
    for nested_key, metric_key in nested_exists:
        nested = payload.get(nested_key)
        if isinstance(nested, Mapping) and nested.get("exists") is True:
            metrics[metric_key] = True
    for payload_key, metric_key in list_nonempty_flags:
        raw = payload.get(payload_key)
        if isinstance(raw, list) and raw:
            metrics[metric_key] = True
    for payload_key, metric_key in float_fields:
        num = as_float(payload.get(payload_key))
        if num is not None:
            metrics[metric_key] = num
    if int_fields:
        apply_nonneg_int_fields(metrics, payload, int_fields)
    for payload_key, metric_key in list_len_fields:
        raw = payload.get(payload_key)
        if isinstance(raw, list):
            metrics[metric_key] = len(raw)
    for payload_key, match_metric, mismatch_metric in bool_match_fields:
        matches = payload.get(payload_key)
        metrics[match_metric] = matches is True
        if matches is False:
            metrics[mismatch_metric] = True
    for opt_spec in optional_int:
        if len(opt_spec) == 3:
            payload_key, metric_key, positive_only = opt_spec
            apply_optional_int_field(
                metrics,
                payload,
                payload_key,
                metric_key,
                positive_only=positive_only,
            )
        else:
            payload_key, metric_key = opt_spec
            apply_optional_int_field(metrics, payload, payload_key, metric_key)
    for payload_key, metric_key in str_present:
        apply_str_present(metrics, payload, payload_key, metric_key)
    for payload_key, metric_key in str_strip_fields:
        stripped = as_stripped_str(payload.get(payload_key))
        if stripped is not None:
            metrics[metric_key] = stripped
    for payload_key, metric_key in bool_value_fields:
        val = payload.get(payload_key)
        if isinstance(val, bool):
            metrics[metric_key] = val
    for tri_spec in env_tri_state:
        if isinstance(tri_spec, str):
            apply_env_tri_state_metrics(metrics, payload, tri_spec)
        else:
            env_key, forces_on_key, forces_off_key, unset_key = tri_spec
            apply_env_tri_state_metrics(
                metrics,
                payload,
                env_key,
                forces_on_key=forces_on_key,
                forces_off_key=forces_off_key,
                unset_key=unset_key,
            )
    for env_payload_key, flag_payload_key, metric_key in env_flags:
        apply_env_flag_metric(
            metrics,
            payload,
            env_payload_key,
            flag_payload_key,
            metric_key,
        )
    if workflow_yaml_file:
        apply_workflow_yaml_file_metrics(metrics, payload)
    if load_error:
        apply_load_error_present(
            metrics,
            payload,
            payload_key=load_error_payload_key,
            metric_key=load_error_metric_key,
        )
    return metrics
