"""Read-only ``agent_evaluator`` workflow + ``HERMES_AGENT_EVALUATOR`` (§14 #15 / fo139)."""

from __future__ import annotations

import csv
import json
import os
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

import hermes_orchestrator.pipeline  # noqa: F401 — break extensions↔orchestrator cycle
from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_workflow_disk import load_workflow_profile_documents
from hermes_orchestrator.workflow_agent_evaluator import parse_agent_evaluator_workflow_block


def _relative_under(repo_root: Path, path: Path) -> str:
    root = repo_root.resolve()
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path.resolve())


def _json_safe_yaml_fragment(raw: object) -> object:
    """Best-effort JSON/streamlit-safe snapshot of a YAML subtree."""
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


def _hermes_agent_evaluator_env_summary() -> dict[str, Any]:
    """Mirror ``RunOrchestrator._maybe_emit_agent_evaluator_stage`` env branch."""
    raw = os.environ.get("HERMES_AGENT_EVALUATOR", "")
    low = raw.strip().lower()
    if not low:
        return {
            "raw": raw,
            "forces_off": False,
            "forces_on": False,
            "unset": True,
        }
    if low in ("0", "false", "no"):
        return {
            "raw": raw,
            "forces_off": True,
            "forces_on": False,
            "unset": False,
        }
    if low in ("1", "true", "yes"):
        return {
            "raw": raw,
            "forces_off": False,
            "forces_on": True,
            "unset": False,
        }
    return {
        "raw": raw,
        "forces_off": False,
        "forces_on": False,
        "unset": True,
        "unrecognised_value": True,
    }


def _hermes_agent_evaluator_auto_promote_env_summary() -> dict[str, Any]:
    """Mirror ``RunOrchestrator._agent_evaluator_auto_promote_env_disabled``."""
    raw = os.environ.get("HERMES_AGENT_EVALUATOR_AUTO_PROMOTE", "")
    low = raw.strip().lower()
    if not low:
        return {
            "raw": raw,
            "disables_auto_promote": False,
            "unset": True,
        }
    if low in ("0", "false", "no"):
        return {
            "raw": raw,
            "disables_auto_promote": True,
            "unset": False,
        }
    return {
        "raw": raw,
        "disables_auto_promote": False,
        "unset": False,
        "unrecognised_value": True,
    }


def _hermes_agent_evaluator_auto_create_env_summary() -> dict[str, Any]:
    """Mirror ``RunOrchestrator._agent_evaluator_auto_create_env_disabled``."""
    raw = os.environ.get("HERMES_AGENT_EVALUATOR_AUTO_CREATE", "")
    low = raw.strip().lower()
    if not low:
        return {
            "raw": raw,
            "disables_auto_create": False,
            "unset": True,
        }
    if low in ("0", "false", "no"):
        return {
            "raw": raw,
            "disables_auto_create": True,
            "unset": False,
        }
    return {
        "raw": raw,
        "disables_auto_create": False,
        "unset": False,
        "unrecognised_value": True,
    }


def _would_emit_agent_evaluator_stage(repo_root: Path, workflow_profile: str | None) -> bool:
    """Same gate as ``_maybe_emit_agent_evaluator_stage`` before persona/catalog checks."""
    env_raw = os.environ.get("HERMES_AGENT_EVALUATOR", "").strip().lower()
    if env_raw in ("0", "false", "no"):
        return False
    env_on = env_raw in ("1", "true", "yes")
    block = parse_agent_evaluator_workflow_block(repo_root, workflow_profile)
    return env_on or block.enabled


def _would_emit_llm_evaluation(repo_root: Path, workflow_profile: str | None) -> bool:
    """Pipeline-aligned: LLM branch when stage would emit, YAML LLM on, and ``HERMES_USE_LLM``."""
    if not _would_emit_agent_evaluator_stage(repo_root, workflow_profile):
        return False
    if os.environ.get("HERMES_USE_LLM", "").strip().lower() not in ("1", "true", "yes"):
        return False
    block = parse_agent_evaluator_workflow_block(repo_root, workflow_profile)
    return block.llm_evaluation_enabled


def agent_evaluator_env_gate_caption(payload: Mapping[str, Any] | None) -> str | None:
    """One-line summary of ``HERMES_AGENT_EVALUATOR`` env gate (unset / kill-switch / force-on)."""
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
    """One-line summary of ``HERMES_AGENT_EVALUATOR_AUTO_PROMOTE`` env gate."""
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
    """Top-level ``version`` int from the selected workflow profile YAML on disk."""
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
    """One-line summary of ``HERMES_AGENT_EVALUATOR_AUTO_CREATE`` env gate."""
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
    """Count of ``true`` bool leaves under ``agent_evaluator`` in workflow YAML."""
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
    """Python type name of the frozen ``agent_evaluator`` YAML value."""
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
    """Whether ``agent_evaluator`` exists on the workflow YAML and ``yaml_parsed_enabled``."""
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
        return (
            "Agent evaluator: workflow YAML key **present**, enabled=**true**."
        )
    if enabled is False:
        return (
            "Agent evaluator: workflow YAML key **present**, enabled=**false**."
        )
    return "Agent evaluator: workflow YAML key **present** (enabled not observable)."


def agent_evaluator_persona_id_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Surface ``yaml_parsed_persona_id`` from the workflow explainer payload."""
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
    """Surface ``yaml_parsed_llm_evaluation_enabled`` when the workflow YAML key is present."""
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
    """Surface ``yaml_parsed_enabled`` when the workflow YAML key is present."""
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


def agent_evaluator_would_emit_caption(payload: Mapping[str, Any] | None) -> str | None:
    """One-line summary of ``would_emit_stage_started`` from the workflow explainer."""
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


def agent_evaluator_workflow_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
) -> dict[str, Any]:
    """Frozen ``agent_evaluator`` YAML vs env vs ``would_emit_stage_started`` (pipeline-aligned)."""
    wf_key = str(workflow_profile).strip() if workflow_profile else ""
    wf_sel: str | None = wf_key if wf_key else None

    workflow_yaml_relpath: str | None = None
    load_error: str | None = None
    yaml_key_present = False
    yaml_value: Any = None
    workflow_yaml_top_level_version_int: int | None = None

    mat = console_config_materializer(repo_root)
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
                if "agent_evaluator" in doc:
                    yaml_key_present = True
                    yaml_value = doc.get("agent_evaluator")
        except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError) as err:
            load_error = str(err)
            yaml_value = None

    block = parse_agent_evaluator_workflow_block(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )
    would_emit = _would_emit_agent_evaluator_stage(repo_root, wf_sel)
    would_emit_llm = _would_emit_llm_evaluation(repo_root, wf_sel)

    yaml_raw_type: str | None
    if yaml_value is None:
        yaml_raw_type = None
    else:
        yaml_raw_type = type(yaml_value).__name__

    yaml_mapping_string_key_count: int | None = None
    yaml_true_bool_value_count: int | None = None
    yaml_false_bool_value_count: int | None = None
    if isinstance(yaml_value, dict):
        yaml_mapping_string_key_count = sum(1 for k in yaml_value if isinstance(k, str))
        yaml_true_bool_value_count = sum(
            1 for v in yaml_value.values() if type(v) is bool and v is True
        )
        yaml_false_bool_value_count = sum(
            1 for v in yaml_value.values() if type(v) is bool and v is False
        )

    ac = block.auto_create_persona
    return {
        "workflow_profile": wf_sel,
        "workflow_yaml_relpath": workflow_yaml_relpath,
        "workflow_yaml_top_level_version_int": workflow_yaml_top_level_version_int,
        "agent_evaluator_yaml_key_present": yaml_key_present,
        "agent_evaluator_yaml_value": _json_safe_yaml_fragment(yaml_value),
        "agent_evaluator_yaml_raw_type": yaml_raw_type,
        "agent_evaluator_yaml_mapping_string_key_count": yaml_mapping_string_key_count,
        "agent_evaluator_yaml_true_bool_value_count": yaml_true_bool_value_count,
        "agent_evaluator_yaml_false_bool_value_count": yaml_false_bool_value_count,
        "yaml_parsed_enabled": block.enabled,
        "yaml_parsed_llm_evaluation_enabled": block.llm_evaluation_enabled,
        "yaml_parsed_persona_id": block.persona_id,
        "yaml_parsed_auto_promote_probation": block.auto_promote_probation,
        "yaml_parsed_auto_create_persona": {
            "enabled": ac.enabled,
            "shelf": ac.shelf,
            "display_name": ac.display_name,
        },
        "HERMES_AGENT_EVALUATOR": _hermes_agent_evaluator_env_summary(),
        "HERMES_AGENT_EVALUATOR_AUTO_PROMOTE": _hermes_agent_evaluator_auto_promote_env_summary(),
        "HERMES_AGENT_EVALUATOR_AUTO_CREATE": _hermes_agent_evaluator_auto_create_env_summary(),
        "would_emit_stage_started": would_emit,
        "would_emit_llm_evaluation": would_emit_llm,
        "load_error": load_error,
    }


def agent_evaluator_export_filename_slug() -> str:
    """Filename slug prefix for agent evaluator explainer exports."""
    return "agent_evaluator"


_AGENT_EVALUATOR_EXPLAINER_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def _agent_evaluator_explainer_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def agent_evaluator_explainer_table_rows(
    payload: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Sorted field/value rows for agent evaluator explainer export."""
    if not isinstance(payload, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key in sorted(str(k) for k in payload.keys()):
        rows.append(
            {
                "field": key,
                "value": _agent_evaluator_explainer_cell(payload.get(key)),
            },
        )
    return rows


def agent_evaluator_explainer_export_json(
    payload: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for agent evaluator explainer payload."""
    if not isinstance(payload, Mapping):
        return "{}"
    return json.dumps(dict(payload), indent=2, ensure_ascii=False)


def agent_evaluator_explainer_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize agent evaluator explainer field/value rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_AGENT_EVALUATOR_EXPLAINER_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _AGENT_EVALUATOR_EXPLAINER_CSV_COLUMNS},
            )
    return buf.getvalue()


_AGENT_EVALUATOR_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def agent_evaluator_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Structured rollup over :func:`agent_evaluator_workflow_explainer_payload` (§14 #15)."""
    metrics: dict[str, Any] = {
        "yaml_key_present": False,
        "yaml_parsed_enabled": False,
        "llm_evaluation_enabled": False,
        "would_emit_llm_evaluation": False,
        "would_emit_stage_started": False,
        "env_forces_on": False,
        "env_forces_off": False,
        "env_unset": True,
        "auto_promote_disabled": False,
        "auto_create_disabled": False,
        "persona_id_present": False,
        "yaml_true_bool_value_count": 0,
        "yaml_false_bool_value_count": 0,
        "load_error_present": False,
        "workflow_yaml_version_int": None,
    }
    if not isinstance(payload, Mapping):
        return metrics
    metrics["yaml_key_present"] = payload.get("agent_evaluator_yaml_key_present") is True
    metrics["yaml_parsed_enabled"] = payload.get("yaml_parsed_enabled") is True
    metrics["llm_evaluation_enabled"] = (
        payload.get("yaml_parsed_llm_evaluation_enabled") is True
    )
    metrics["would_emit_stage_started"] = payload.get("would_emit_stage_started") is True
    metrics["would_emit_llm_evaluation"] = (
        payload.get("would_emit_llm_evaluation") is True
    )
    env = payload.get("HERMES_AGENT_EVALUATOR")
    if isinstance(env, dict):
        metrics["env_forces_on"] = env.get("forces_on") is True
        metrics["env_forces_off"] = env.get("forces_off") is True
        metrics["env_unset"] = env.get("unset") is True
    ap = payload.get("HERMES_AGENT_EVALUATOR_AUTO_PROMOTE")
    if isinstance(ap, dict):
        metrics["auto_promote_disabled"] = ap.get("disables_auto_promote") is True
    ac = payload.get("HERMES_AGENT_EVALUATOR_AUTO_CREATE")
    if isinstance(ac, dict):
        metrics["auto_create_disabled"] = ac.get("disables_auto_create") is True
    pid = payload.get("yaml_parsed_persona_id")
    metrics["persona_id_present"] = isinstance(pid, str) and bool(pid.strip())
    for key, out_key in (
        ("agent_evaluator_yaml_true_bool_value_count", "yaml_true_bool_value_count"),
        ("agent_evaluator_yaml_false_bool_value_count", "yaml_false_bool_value_count"),
    ):
        raw = payload.get(key)
        if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
            metrics[out_key] = raw
    err = payload.get("load_error")
    metrics["load_error_present"] = isinstance(err, str) and bool(err.strip())
    ver = payload.get("workflow_yaml_top_level_version_int")
    if isinstance(ver, int) and not isinstance(ver, bool):
        metrics["workflow_yaml_version_int"] = ver
    return metrics


def agent_evaluator_workflow_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {
            "field": "YAML key present",
            "value": str(metrics.get("yaml_key_present", False)).lower(),
        },
        {
            "field": "YAML parsed enabled",
            "value": str(metrics.get("yaml_parsed_enabled", False)).lower(),
        },
        {
            "field": "Would emit stage",
            "value": str(metrics.get("would_emit_stage_started", False)).lower(),
        },
        {
            "field": "Env forces on",
            "value": str(metrics.get("env_forces_on", False)).lower(),
        },
        {
            "field": "Env forces off",
            "value": str(metrics.get("env_forces_off", False)).lower(),
        },
        {
            "field": "Env unset",
            "value": str(metrics.get("env_unset", True)).lower(),
        },
        {
            "field": "Persona id present",
            "value": str(metrics.get("persona_id_present", False)).lower(),
        },
        {
            "field": "LLM evaluation enabled",
            "value": str(metrics.get("llm_evaluation_enabled", False)).lower(),
        },
        {
            "field": "Would emit LLM branch",
            "value": str(metrics.get("would_emit_llm_evaluation", False)).lower(),
        },
        {
            "field": "Auto-promote disabled (env)",
            "value": str(metrics.get("auto_promote_disabled", False)).lower(),
        },
        {
            "field": "Auto-create disabled (env)",
            "value": str(metrics.get("auto_create_disabled", False)).lower(),
        },
        {
            "field": "YAML true bool count",
            "value": str(metrics.get("yaml_true_bool_value_count", 0)),
        },
        {
            "field": "YAML false bool count",
            "value": str(metrics.get("yaml_false_bool_value_count", 0)),
        },
    ]
    ver = metrics.get("workflow_yaml_version_int")
    if isinstance(ver, int) and not isinstance(ver, bool):
        rows.append({"field": "Workflow YAML version", "value": str(ver)})
    if metrics.get("load_error_present") is True:
        rows.append({"field": "Load error", "value": "yes"})
    return rows


def agent_evaluator_workflow_explainer_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON export of workflow explainer operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def agent_evaluator_workflow_explainer_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize workflow explainer operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_AGENT_EVALUATOR_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _AGENT_EVALUATOR_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def agent_evaluator_workflow_explainer_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption for workflow explainer rollup metrics."""
    if not isinstance(metrics, Mapping):
        return None
    parts: list[str] = []
    if metrics.get("would_emit_stage_started") is True:
        parts.append("stage **would emit**")
    elif metrics.get("env_forces_off") is True:
        parts.append("env **forces off**")
    elif metrics.get("env_forces_on") is True:
        parts.append("env **forces on**")
    if metrics.get("yaml_parsed_enabled") is True:
        parts.append("YAML enabled")
    if metrics.get("llm_evaluation_enabled") is True:
        parts.append("LLM evaluation **on**")
    if metrics.get("would_emit_llm_evaluation") is True:
        parts.append("LLM branch **would emit**")
    if metrics.get("auto_promote_disabled") is True:
        parts.append("auto-promote **disabled** (env)")
    if metrics.get("auto_create_disabled") is True:
        parts.append("auto-create **disabled** (env)")
    true_b = metrics.get("yaml_true_bool_value_count", 0)
    if isinstance(true_b, int) and not isinstance(true_b, bool) and true_b > 0:
        parts.append(f"**{true_b}** YAML ``true`` bool(s)")
    if metrics.get("load_error_present") is True:
        parts.append("load error")
    if not parts:
        return None
    return "Agent evaluator explainer metrics: " + ", ".join(parts) + "."


def agent_evaluator_workflow_explainer_operator_metrics_export_filename_slug() -> str:
    """Stable slug for workflow explainer operator metrics downloads."""
    return "agent_evaluator_workflow_explainer_operator_metrics"
