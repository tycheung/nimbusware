from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any


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
        if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
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
    if not isinstance(raw, int) or isinstance(raw, bool):
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
    raw = payload.get(payload_key)
    metrics[metric_key] = isinstance(raw, str) and bool(raw.strip())


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
