from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from agent_core.coercion import as_float, as_int, as_stripped_str, is_number, is_strict_int


def default_operator_metrics(defaults: Mapping[str, Any]) -> dict[str, Any]:
    return dict(defaults)


def apply_bool_payload_fields(
    metrics: dict[str, Any],
    payload: Mapping[str, Any],
    fields: Sequence[tuple[str, str]],
) -> None:
    for payload_key, metric_key in fields:
        metrics[metric_key] = payload.get(payload_key) is True


def apply_nested_bool_fields(
    metrics: dict[str, Any],
    payload: Mapping[str, Any],
    nested_key: str,
    fields: Sequence[tuple[str, str]],
) -> None:
    nested = payload.get(nested_key)
    if not isinstance(nested, Mapping):
        return
    for nested_field, metric_key in fields:
        metrics[metric_key] = nested.get(nested_field) is True


def apply_nonneg_int_fields(
    metrics: dict[str, Any],
    payload: Mapping[str, Any],
    fields: Sequence[tuple[str, str]],
) -> None:
    for payload_key, metric_key in fields:
        raw = payload.get(payload_key)
        if is_strict_int(raw) and raw >= 0:
            metrics[metric_key] = raw


def apply_optional_int_field(
    metrics: dict[str, Any],
    payload: Mapping[str, Any],
    payload_key: str,
    metric_key: str,
    *,
    positive_only: bool = False,
) -> None:
    raw = payload.get(payload_key)
    if not is_strict_int(raw):
        return
    if positive_only and raw <= 0:
        return
    metrics[metric_key] = raw


def apply_load_error_present(
    metrics: dict[str, Any],
    payload: Mapping[str, Any],
    *,
    payload_key: str = "load_error",
    metric_key: str = "load_error_present",
) -> None:
    err = payload.get(payload_key)
    metrics[metric_key] = isinstance(err, str) and bool(err.strip())


def apply_str_present(
    metrics: dict[str, Any],
    payload: Mapping[str, Any],
    payload_key: str,
    metric_key: str,
) -> None:
    metrics[metric_key] = as_stripped_str(payload.get(payload_key)) is not None


def metrics_table_rows(
    metrics: Mapping[str, Any] | None,
    rows: Sequence[tuple[str, str]],
    *,
    bool_lower: bool = True,
    include_when: Callable[[Mapping[str, Any], str], bool] | None = None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    out: list[dict[str, str]] = []
    for label, metric_key in rows:
        if include_when is not None and not include_when(metrics, metric_key):
            continue
        val = metrics.get(metric_key)
        if val is None:
            continue
        if isinstance(val, bool) and bool_lower:
            cell = str(val).lower()
        else:
            cell = str(val)
        out.append({"field": label, "value": cell})
    return out


def metrics_caption(prefix: str, parts: Sequence[str]) -> str | None:
    if not parts:
        return None
    return prefix + ", ".join(parts) + "."


def apply_env_tri_state_metrics(
    metrics: dict[str, Any],
    payload: Mapping[str, Any],
    env_payload_key: str,
    *,
    forces_on_key: str = "env_forces_on",
    forces_off_key: str = "env_forces_off",
    unset_key: str = "env_unset",
) -> None:
    env = payload.get(env_payload_key)
    if not isinstance(env, Mapping):
        return
    metrics[forces_on_key] = env.get("forces_on") is True
    metrics[forces_off_key] = env.get("forces_off") is True
    metrics[unset_key] = env.get("unset") is True


def apply_workflow_yaml_file_metrics(
    metrics: dict[str, Any],
    payload: Mapping[str, Any],
    *,
    version_payload_key: str = "workflow_yaml_top_level_version_int",
    bytes_payload_key: str = "workflow_yaml_file_bytes",
    version_metric_key: str = "workflow_yaml_version_int",
    bytes_metric_key: str = "workflow_yaml_file_bytes",
) -> None:
    apply_optional_int_field(
        metrics,
        payload,
        version_payload_key,
        version_metric_key,
    )
    apply_nonneg_int_fields(metrics, payload, ((bytes_payload_key, bytes_metric_key),))


def apply_env_flag_metric(
    metrics: dict[str, Any],
    payload: Mapping[str, Any],
    env_payload_key: str,
    flag_payload_key: str,
    metric_key: str,
) -> None:
    env = payload.get(env_payload_key)
    if isinstance(env, Mapping):
        metrics[metric_key] = env.get(flag_payload_key) is True
