from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.mapping import load_error_text
from nimbusware_console.explainer_core.env_captions import (
    env_disable_registry_caption,
    env_tri_state_registry_caption,
)
from nimbusware_console.explainer_core.field_caption import (
    payload_nonempty_str_caption,
    payload_nonneg_int_caption,
)


def agent_evaluator_env_gate_caption(payload: Mapping[str, Any] | None) -> str | None:
    return env_tri_state_registry_caption(
        payload,
        "NIMBUSWARE_AGENT_EVALUATOR",
        "agent_evaluator",
    )


def agent_evaluator_auto_promote_env_gate_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return env_disable_registry_caption(
        payload,
        "NIMBUSWARE_AGENT_EVALUATOR_AUTO_PROMOTE",
        "agent_evaluator_auto_promote",
    )


def agent_evaluator_workflow_yaml_version_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    from nimbusware_console.explainer_core.yaml_version_caption import workflow_yaml_version_caption

    return workflow_yaml_version_caption(payload, label="Agent evaluator")


def agent_evaluator_auto_create_env_gate_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return env_disable_registry_caption(
        payload,
        "NIMBUSWARE_AGENT_EVALUATOR_AUTO_CREATE",
        "agent_evaluator_auto_create",
    )


def agent_evaluator_yaml_true_bool_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonneg_int_caption(
        payload,
        "agent_evaluator_yaml_true_bool_value_count",
        "Agent evaluator workflow YAML enabled: true leaf count: **{value}**.",
    )


def agent_evaluator_yaml_raw_type_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonempty_str_caption(
        payload,
        "agent_evaluator_yaml_raw_type",
        "Agent evaluator workflow YAML raw type: **{value}**.",
    )


def agent_evaluator_yaml_key_present_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if load_error_text(payload) is not None:
        return None
    present = payload.get("agent_evaluator_yaml_key_present")
    if present is not True:
        return "Agent evaluator: workflow YAML key **absent** on this profile."
    enabled = payload.get("yaml_parsed_enabled")
    if enabled is True:
        return "Agent evaluator: workflow YAML key **present**, enabled=**true**."
    if enabled is False:
        return "Agent evaluator: workflow YAML key **present**, enabled=**false**."
    return "Agent evaluator: workflow YAML key **present** (enabled not observable)."


def agent_evaluator_persona_id_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return payload_nonempty_str_caption(
        payload,
        "yaml_parsed_persona_id",
        "Agent evaluator persona_id: `{value}`.",
    )


def agent_evaluator_llm_evaluation_enabled_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if load_error_text(payload) is not None:
        return None
    if payload.get("agent_evaluator_yaml_key_present") is not True:
        return None
    enabled = payload.get("yaml_parsed_llm_evaluation_enabled")
    if not isinstance(enabled, bool):
        return None
    if enabled:
        return (
            "Agent evaluator LLM policy branch: workflow ``llm_evaluation_enabled`` is **on** "
            "(requires ``NIMBUSWARE_USE_LLM`` at runtime)."
        )
    return (
        "Agent evaluator LLM policy branch: workflow ``llm_evaluation_enabled`` is **off** "
        "(rules-only evaluation path)."
    )


def agent_evaluator_yaml_parsed_enabled_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if load_error_text(payload) is not None:
        return None
    if payload.get("agent_evaluator_yaml_key_present") is not True:
        return None
    enabled = payload.get("yaml_parsed_enabled")
    if not isinstance(enabled, bool):
        return None
    return f"Agent evaluator workflow enabled: **{str(enabled).lower()}**."


def agent_evaluator_probation_automation_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if load_error_text(payload) is not None:
        return None
    enabled = payload.get("yaml_parsed_probation_automation_enabled")
    if enabled is True:
        return (
            "Probation automation: workflow ``probation_automation.enabled`` is **on** "
            "(auto-shelve / promote notice follow env and reliability thresholds)."
        )
    if enabled is False:
        return "Probation automation: workflow ``probation_automation.enabled`` is **off**."
    for key, label in (
        ("NIMBUSWARE_PROBATION_AUTO_SHELVE", "auto-shelve"),
        ("NIMBUSWARE_PROBATION_NOTIFY_BEFORE_PROMOTE", "promote notice"),
    ):
        env = payload.get(key)
        if not isinstance(env, Mapping):
            continue
        if env.get("disables_feature"):
            raw = env.get("raw")
            detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
            return f"Probation automation env: **{key}** disables {label}{detail}."
    return None


def agent_evaluator_would_emit_caption(payload: Mapping[str, Any] | None) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if load_error_text(payload) is not None:
        return None
    would = payload.get("would_emit_stage_started")
    if would is True:
        return (
            "Agent evaluator: **would emit** ``stage.started`` for this profile "
            "(env and/or workflow YAML gate on)."
        )
    if would is False:
        return (
            "Agent evaluator: **would not emit** ``stage.started`` "
            "(env kill-switch or workflow YAML gate off)."
        )
    return None
