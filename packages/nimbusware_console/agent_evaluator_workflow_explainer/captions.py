from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def agent_evaluator_env_gate_caption(payload: Mapping[str, Any] | None) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    env = payload.get("HERMES_AGENT_EVALUATOR")
    if not isinstance(env, Mapping):
        return None
    if env.get("forces_off"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Agent evaluator env: **HERMES_AGENT_EVALUATOR** kill-switch active"
            f"{detail} — stage.started will not emit from env alone."
        )
    if env.get("forces_on"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Agent evaluator env: **HERMES_AGENT_EVALUATOR** force-on"
            f"{detail} — stage.started may emit when workflow gate allows."
        )
    if env.get("unset"):
        return (
            "Agent evaluator env: **HERMES_AGENT_EVALUATOR** unset — "
            "workflow YAML ``agent_evaluator.enabled`` controls emission."
        )
    if env.get("unrecognised_value"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Agent evaluator env: **HERMES_AGENT_EVALUATOR** unrecognised value"
            f"{detail} — treated like unset; workflow YAML gate applies."
        )
    return None


def agent_evaluator_auto_promote_env_gate_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    env = payload.get("HERMES_AGENT_EVALUATOR_AUTO_PROMOTE")
    if not isinstance(env, Mapping):
        return None
    if env.get("disables_auto_promote"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Agent evaluator auto-promote env: "
            "**HERMES_AGENT_EVALUATOR_AUTO_PROMOTE** kill-switch active"
            f"{detail}."
        )
    if env.get("unset"):
        return (
            "Agent evaluator auto-promote env: "
            "**HERMES_AGENT_EVALUATOR_AUTO_PROMOTE** unset — "
            "workflow ``agent_evaluator.auto_promote_probation`` controls promotion."
        )
    if env.get("unrecognised_value"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Agent evaluator auto-promote env: "
            "**HERMES_AGENT_EVALUATOR_AUTO_PROMOTE** unrecognised value"
            f"{detail} — treated like unset."
        )
    return None


def agent_evaluator_workflow_yaml_version_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    raw = payload.get("workflow_yaml_top_level_version_int")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        return None
    return f"Agent evaluator workflow YAML top-level version: **{raw}**."


def agent_evaluator_auto_create_env_gate_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    env = payload.get("HERMES_AGENT_EVALUATOR_AUTO_CREATE")
    if not isinstance(env, Mapping):
        return None
    if env.get("disables_auto_create"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Agent evaluator auto-create env: "
            "**HERMES_AGENT_EVALUATOR_AUTO_CREATE** kill-switch active"
            f"{detail}."
        )
    if env.get("unset"):
        return (
            "Agent evaluator auto-create env: "
            "**HERMES_AGENT_EVALUATOR_AUTO_CREATE** unset — "
            "workflow ``agent_evaluator.auto_create_persona`` controls creation."
        )
    if env.get("unrecognised_value"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Agent evaluator auto-create env: "
            "**HERMES_AGENT_EVALUATOR_AUTO_CREATE** unrecognised value"
            f"{detail} — treated like unset."
        )
    return None


def agent_evaluator_yaml_true_bool_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    raw = payload.get("agent_evaluator_yaml_true_bool_value_count")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Agent evaluator workflow YAML enabled: true leaf count: **{raw}**."


def agent_evaluator_yaml_raw_type_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    raw = payload.get("agent_evaluator_yaml_raw_type")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Agent evaluator workflow YAML raw type: **{text}**."


def agent_evaluator_yaml_key_present_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
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
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    raw = payload.get("yaml_parsed_persona_id")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Agent evaluator persona_id: `{text}`."


def agent_evaluator_llm_evaluation_enabled_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    if payload.get("agent_evaluator_yaml_key_present") is not True:
        return None
    enabled = payload.get("yaml_parsed_llm_evaluation_enabled")
    if not isinstance(enabled, bool):
        return None
    if enabled:
        return (
            "Agent evaluator LLM policy branch: workflow ``llm_evaluation_enabled`` is **on** "
            "(requires ``HERMES_USE_LLM`` at runtime)."
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
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
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
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
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
        ("HERMES_PROBATION_AUTO_SHELVE", "auto-shelve"),
        ("HERMES_PROBATION_NOTIFY_BEFORE_PROMOTE", "promote notice"),
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
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
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
