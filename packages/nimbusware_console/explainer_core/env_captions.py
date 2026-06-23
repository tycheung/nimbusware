from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from typing_extensions import TypedDict

from agent_core.mapping import load_error_text
from nimbusware_console.explainer_core.env_summaries import env_tri_state_summary


class EnvTriStateTemplate(TypedDict, total=False):
    label: str
    forces_off_text: str
    forces_on_text: str
    unset_text: str
    unrecognised_text: str
    unset_key: str


class EnvDisableTemplate(TypedDict):
    active_text: str
    unset_text: str
    unrecognised_text: str


ENV_TRI_STATE_TEMPLATES: dict[str, EnvTriStateTemplate] = {
    "agent_evaluator": {
        "label": "Agent evaluator",
        "forces_off_text": (
            "Agent evaluator env: **{env_key}** kill-switch active"
            "{detail} — stage.started will not emit from env alone."
        ),
        "forces_on_text": (
            "Agent evaluator env: **{env_key}** force-on"
            "{detail} — stage.started may emit when workflow gate allows."
        ),
        "unset_text": (
            "Agent evaluator env: **{env_key}** unset — "
            "workflow YAML ``agent_evaluator.enabled`` controls emission."
        ),
        "unrecognised_text": (
            "Agent evaluator env: **{env_key}** unrecognised value"
            "{detail} — treated like unset; workflow YAML gate applies."
        ),
    },
    "security_scan_metadata": {
        "label": "Security scan metadata",
        "forces_off_text": (
            "Security scan metadata env: **{env_key}** kill-switch active{detail}."
        ),
        "forces_on_text": "Security scan metadata env: **{env_key}** force-on{detail}.",
        "unset_text": (
            "Security scan metadata env: **{env_key}** unset — "
            "workflow YAML controls **effective_enabled**."
        ),
        "unrecognised_text": (
            "Security scan metadata env: **{env_key}** unrecognised value"
            "{detail} — treated like unset."
        ),
        "unset_key": "unset_follows_yaml",
    },
    "integration_adapter_writer": {
        "label": "Integration Adapter Writer env",
        "forces_off_text": (
            "Integration Adapter Writer env: **{env_key}** "
            "kill-switch active{detail} — workflow enable ignored."
        ),
        "forces_on_text": (
            "Integration Adapter Writer env: **{env_key}** "
            "force-on{detail} — scaffold may activate when pipeline wiring lands."
        ),
        "unset_text": (
            "Integration Adapter Writer env: unset — "
            "workflow ``integration_adapter_writer.enabled`` controls scaffold."
        ),
        "unrecognised_text": "",
    },
}

ENV_DISABLE_TEMPLATES: dict[str, EnvDisableTemplate] = {
    "agent_evaluator_auto_promote": {
        "active_text": (
            "Agent evaluator auto-promote env: **{env_key}** kill-switch active{detail}."
        ),
        "unset_text": (
            "Agent evaluator auto-promote env: **{env_key}** unset — "
            "workflow ``agent_evaluator.auto_promote_probation`` controls promotion."
        ),
        "unrecognised_text": (
            "Agent evaluator auto-promote env: **{env_key}** unrecognised value"
            "{detail} — treated like unset."
        ),
    },
    "agent_evaluator_auto_create": {
        "active_text": (
            "Agent evaluator auto-create env: **{env_key}** kill-switch active{detail}."
        ),
        "unset_text": (
            "Agent evaluator auto-create env: **{env_key}** unset — "
            "workflow ``agent_evaluator.auto_create_persona`` controls creation."
        ),
        "unrecognised_text": (
            "Agent evaluator auto-create env: **{env_key}** unrecognised value"
            "{detail} — treated like unset."
        ),
    },
}


def _raw_detail(env: Mapping[str, Any]) -> str:
    raw = env.get("raw")
    if isinstance(raw, str) and raw.strip():
        return f" (raw={raw!r})"
    return ""


def env_tri_state_yaml_follows_summary(env_key: str) -> dict[str, object]:
    base = dict(env_tri_state_summary(env_key))
    base["unset_follows_yaml"] = bool(base.get("unset"))
    return base


def env_tri_state_gate_caption(
    payload: Mapping[str, Any] | None,
    env_key: str,
    *,
    label: str,
    forces_off_text: str,
    forces_on_text: str,
    unset_text: str,
    unrecognised_text: str,
    unset_key: str = "unset",
) -> str | None:
    if load_error_text(payload) is not None:
        return None
    env = payload.get(env_key) if isinstance(payload, Mapping) else None
    if not isinstance(env, Mapping):
        return None
    detail = _raw_detail(env)
    if env.get("forces_off"):
        return forces_off_text.format(env_key=env_key, detail=detail)
    if env.get("forces_on"):
        return forces_on_text.format(env_key=env_key, detail=detail)
    if env.get(unset_key):
        return unset_text.format(env_key=env_key)
    if env.get("unrecognised_value"):
        return unrecognised_text.format(env_key=env_key, detail=detail)
    return None


def env_disable_flag_gate_caption(
    payload: Mapping[str, Any] | None,
    env_key: str,
    *,
    active_text: str,
    unset_text: str,
    unrecognised_text: str,
) -> str | None:
    if load_error_text(payload) is not None:
        return None
    env = payload.get(env_key) if isinstance(payload, Mapping) else None
    if not isinstance(env, Mapping):
        return None
    detail = _raw_detail(env)
    if (
        env.get("disables_feature")
        or env.get("disables_auto_promote")
        or env.get("disables_auto_create")
    ):
        return active_text.format(env_key=env_key, detail=detail)
    if env.get("unset"):
        return unset_text.format(env_key=env_key)
    if env.get("unrecognised_value"):
        return unrecognised_text.format(env_key=env_key, detail=detail)
    return None


def env_tri_state_registry_caption(
    payload: Mapping[str, Any] | None,
    env_key: str,
    template_key: str,
) -> str | None:
    template = ENV_TRI_STATE_TEMPLATES[template_key]
    return env_tri_state_gate_caption(payload, env_key, **template)


def env_disable_registry_caption(
    payload: Mapping[str, Any] | None,
    env_key: str,
    template_key: str,
) -> str | None:
    template = ENV_DISABLE_TEMPLATES[template_key]
    return env_disable_flag_gate_caption(payload, env_key, **template)
