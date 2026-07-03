from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from agent_core.mapping import field_error_text, load_error_text


def payload_mapping(payload: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    return payload if isinstance(payload, Mapping) else None


def payload_load_error_clear(payload: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    body = payload_mapping(payload)
    if body is None or load_error_text(body) is not None:
        return None
    return body


def escalation_policy_yaml_ready(payload: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    body = payload_mapping(payload)
    if body is None:
        return None
    if field_error_text(body, "escalation_policy_yaml_load_error") is not None:
        return None
    if body.get("escalation_policy_yaml_path_exists") is not True:
        return None
    return body


def payload_nonneg_int_caption(
    payload: Mapping[str, Any] | None,
    field_key: str,
    template: str,
    *,
    guard: Callable[[Mapping[str, Any] | None], Mapping[str, Any] | None] | None = None,
    min_value: int = 0,
    unit: Callable[[int], str] | None = None,
) -> str | None:
    body = (guard or payload_load_error_clear)(payload)
    if body is None:
        return None
    raw = body.get(field_key)
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < min_value:
        return None
    if unit is not None:
        return template.format(value=raw, unit=unit(raw))
    return template.format(value=raw)


def payload_bool_shape_caption(
    payload: Mapping[str, Any] | None,
    field_key: str,
    *,
    true_text: str,
    false_text: str,
    guard: Callable[[Mapping[str, Any] | None], Mapping[str, Any] | None] | None = None,
) -> str | None:
    body = (guard or payload_mapping)(payload)
    if body is None:
        return None
    value = body.get(field_key)
    if value is True:
        return true_text
    if value is False:
        return false_text
    return None


def payload_nonempty_str_caption(
    payload: Mapping[str, Any] | None,
    field_key: str,
    template: str,
    *,
    guard: Callable[[Mapping[str, Any] | None], Mapping[str, Any] | None] | None = None,
) -> str | None:
    body = (guard or payload_load_error_clear)(payload)
    if body is None:
        return None
    raw = body.get(field_key)
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return template.format(value=text)
