"""Read-only breakdown of integrator min-score + gate emission sources.

Mirrors :func:`effective_integrator_min_score_to_pass` and the preconditions in
``RunOrchestrator._emit_bundle_integrator_gate`` so operators can see why preview
min score may differ when a pasted fragment sets ``min_score_to_pass``.
"""

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
from nimbusware_console.integrator_workflow_preview import (
    parse_integrator_gate_yaml_fragment,
    preview_effective_min_score_to_pass,
)
from hermes_orchestrator.integrator_gate import (
    effective_integrator_min_score_to_pass,
    integrator_gate_workflow_enabled,
    load_integrator_gate_emit_enabled,
    load_integrator_gate_workflow_block,
    parse_integrator_gate_min_score_to_pass,
    parse_integrator_gate_project_tags,
)
from hermes_orchestrator.merge import load_yaml
from hermes_orchestrator.workflow_profiles import workflow_profile_path


def _relative_under(repo_root: Path, path: Path) -> str:
    root = repo_root.resolve()
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path.resolve())


def _thresholds_snapshot(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any]:
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        try:
            raw = config_materializer.get_integrator_thresholds()
        except KeyError:
            return {
                "relpath": "configs/integrator/thresholds.yaml",
                "exists": False,
                "source": "materializer",
                "enabled": None,
                "min_score_to_pass": None,
                "top_level_version_int": None,
            }
        snap: dict[str, Any] = {
            "relpath": "configs/integrator/thresholds.yaml",
            "exists": True,
            "source": "materializer",
            "thresholds_yaml_file_bytes": None,
        }
        if not isinstance(raw, dict):
            snap["enabled"] = None
            snap["min_score_to_pass"] = None
            snap["top_level_version_int"] = None
            return snap
        snap["enabled"] = bool(raw.get("enabled", False))
        try:
            snap["min_score_to_pass"] = float(raw.get("min_score_to_pass", 0.0))
        except (TypeError, ValueError):
            snap["min_score_to_pass"] = None
        raw_v = raw.get("version")
        snap["top_level_version_int"] = (
            int(raw_v) if type(raw_v) is int and not isinstance(raw_v, bool) else None
        )
        return snap
    return _thresholds_disk_snapshot(repo_root)


def _thresholds_disk_snapshot(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "configs" / "integrator" / "thresholds.yaml"
    snap: dict[str, Any] = {
        "relpath": "configs/integrator/thresholds.yaml",
        "exists": path.is_file(),
        "thresholds_yaml_file_bytes": None,
    }
    if path.is_file():
        try:
            snap["thresholds_yaml_file_bytes"] = int(path.stat().st_size)
        except OSError:
            snap["thresholds_yaml_file_bytes"] = None
    if not path.is_file():
        snap["enabled"] = None
        snap["min_score_to_pass"] = None
        snap["top_level_version_int"] = None
        return snap
    raw = load_yaml(path)
    if not isinstance(raw, dict):
        snap["enabled"] = None
        snap["min_score_to_pass"] = None
        snap["top_level_version_int"] = None
        return snap
    snap["enabled"] = bool(raw.get("enabled", False))
    try:
        snap["min_score_to_pass"] = float(raw.get("min_score_to_pass", 0.0))
    except (TypeError, ValueError):
        snap["min_score_to_pass"] = None
    raw_v = raw.get("version")
    snap["top_level_version_int"] = (
        int(raw_v) if type(raw_v) is int and not isinstance(raw_v, bool) else None
    )
    return snap


def _env_min_score_to_pass_breakdown() -> dict[str, Any]:
    raw = os.environ.get("HERMES_INTEGRATOR_MIN_SCORE_TO_PASS", "").strip()
    if not raw:
        return {
            "raw": "",
            "parses": False,
            "value": None,
            "invalid": False,
            "overrides_yaml": False,
        }
    try:
        v = max(0.0, min(1.0, float(raw)))
    except ValueError:
        return {
            "raw": raw,
            "parses": False,
            "value": None,
            "invalid": True,
            "overrides_yaml": False,
        }
    return {"raw": raw, "parses": True, "value": v, "invalid": False, "overrides_yaml": True}


def _emit_integrator_gate_breakdown(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any]:
    """Match ``_emit_bundle_integrator_gate`` guardrails (no side effects)."""
    env_raw = os.environ.get("HERMES_EMIT_INTEGRATOR_GATE", "")
    env = env_raw.strip().lower()
    forces_off = env in ("0", "false", "no")
    forces_on = env in ("1", "true", "yes")
    yaml_on = load_integrator_gate_emit_enabled(
        repo_root,
        config_materializer=config_materializer,
    )
    wf_on = integrator_gate_workflow_enabled(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    has_thr = False
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        try:
            config_materializer.get_integrator_thresholds()
            has_thr = True
        except KeyError:
            has_thr = False
    else:
        thr_path = repo_root / "configs" / "integrator" / "thresholds.yaml"
        has_thr = thr_path.is_file()
    if forces_off:
        would_emit = False
        reason = "HERMES_EMIT_INTEGRATOR_GATE forces off (0/false/no)"
    elif not has_thr:
        would_emit = False
        reason = "configs/integrator/thresholds.yaml missing"
    elif forces_on or yaml_on or wf_on:
        would_emit = True
        reason = (
            "thresholds file present and at least one of: HERMES_EMIT_INTEGRATOR_GATE "
            "force-on, thresholds.yaml enabled, workflow integrator_gate.enabled"
        )
    else:
        would_emit = False
        reason = (
            "no emission: env not force-on, thresholds.enabled false, "
            "workflow integrator_gate.enabled false"
        )
    return {
        "HERMES_EMIT_INTEGRATOR_GATE": env_raw,
        "forces_off": forces_off,
        "forces_on": forces_on,
        "catalog_thresholds_yaml_enabled": yaml_on,
        "workflow_integrator_gate_enabled": wf_on,
        "thresholds_yaml_exists": has_thr,
        "would_emit_integrator_gate_event": would_emit,
        "not_emit_reason": None if would_emit else reason,
    }


def integrator_threshold_gate_emission_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """One-line summary of whether a ``gate.decision.emitted`` would be written."""
    if not isinstance(payload, Mapping):
        return None
    emission = payload.get("gate_event_emission")
    if not isinstance(emission, Mapping):
        return None
    would = emission.get("would_emit_integrator_gate_event")
    if would is True:
        return (
            "Integrator gate emission: **would emit** ``gate.decision.emitted`` for this "
            "profile (thresholds file present and at least one enable path is on)."
        )
    if would is False:
        reason = emission.get("not_emit_reason")
        tail = f" ({reason})" if isinstance(reason, str) and reason.strip() else ""
        return f"Integrator gate emission: **would not emit**{tail}."
    return None


def integrator_threshold_thresholds_yaml_version_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Top-level ``version`` int from ``configs/integrator/thresholds.yaml`` on disk."""
    if not isinstance(payload, Mapping):
        return None
    thr = payload.get("thresholds_yaml")
    if not isinstance(thr, Mapping):
        return None
    if thr.get("exists") is not True:
        return None
    raw = thr.get("top_level_version_int")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        return None
    return f"Integrator thresholds.yaml on-disk version: **{raw}**."


def integrator_threshold_min_score_agreement_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """One-line pipeline vs Streamlit preview ``min_score_to_pass`` agreement."""
    if not isinstance(payload, Mapping):
        return None
    pipe = payload.get("pipeline_effective_min_score_to_pass")
    preview = payload.get("streamlit_preview_effective_min_score_to_pass")
    if not isinstance(pipe, (int, float)) or isinstance(pipe, bool):
        return None
    if not isinstance(preview, (int, float)) or isinstance(preview, bool):
        return None
    if pipe == preview:
        note = payload.get("min_score_agreement_note")
        if isinstance(note, str) and note.strip():
            return "Min score: " + note.strip() + "."
        return f"Min score agreement: pipeline and preview both **{pipe}**."
    margin = preview - pipe
    return (
        f"Min score mismatch: pipeline **{pipe}**, preview **{preview}** "
        f"(preview minus pipeline: **{margin:+.6g}**)."
    )


_INTEGRATOR_THRESHOLD_PASTE_PARSE_ERROR_CAP = 3


def integrator_threshold_paste_parse_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Surface non-empty ``paste_parse_errors`` from the threshold explainer payload."""
    if not isinstance(payload, Mapping):
        return None
    raw = payload.get("paste_parse_errors")
    if not isinstance(raw, list) or not raw:
        return None
    errs: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text and text not in errs:
            errs.append(text)
    if not errs:
        return None
    n = len(errs)
    word = "error" if n == 1 else "errors"
    cap = _INTEGRATOR_THRESHOLD_PASTE_PARSE_ERROR_CAP
    if n <= cap:
        body = "; ".join(errs)
    else:
        head = errs[:cap]
        rest = n - cap
        body = "; ".join(head) + f"; +{rest} more"
    return (
        f"Integrator threshold: pasted gate YAML has **{n}** parse {word}: {body}."
    )


def integrator_threshold_project_tags_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """One-line ``integrator_gate.project_tags`` list length on the selected workflow profile."""
    if not isinstance(payload, Mapping):
        return None
    wf = payload.get("workflow_integrator_gate")
    if not isinstance(wf, Mapping) or not wf.get("block_present"):
        return None
    n = wf.get("project_tags_list_length")
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        return None
    if n == 0:
        return "Integrator gate project_tags: **0** tag(s) on workflow profile."
    suffix = "tag" if n == 1 else "tags"
    return f"Integrator gate project_tags: **{n}** {suffix} on workflow profile."


def integrator_threshold_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
    pasted_yaml: str,
) -> dict[str, Any]:
    """JSON-serializable snapshot for Streamlit ``st.json`` / tables."""
    wf_key = str(workflow_profile).strip() if workflow_profile else ""
    wf_sel: str | None = wf_key if wf_key else None

    pasted_block, paste_errs = parse_integrator_gate_yaml_fragment(pasted_yaml)

    mat = console_config_materializer(repo_root)

    workflow_yaml_relpath: str | None = None
    if wf_sel:
        try:
            if mat is not None:
                workflow_yaml_relpath = f"configs/workflows/{wf_sel}.yaml"
            else:
                wp = workflow_profile_path(repo_root, wf_sel)
                workflow_yaml_relpath = _relative_under(repo_root, wp)
        except (FileNotFoundError, OSError, ValueError):
            workflow_yaml_relpath = None

    wf_block = load_integrator_gate_workflow_block(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )
    wf_min = parse_integrator_gate_min_score_to_pass(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )
    wf_tags = parse_integrator_gate_project_tags(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )
    wf_project_tags_count: int | None = None
    if isinstance(wf_block, dict):
        raw_tags = wf_block.get("project_tags")
        if isinstance(raw_tags, list):
            wf_project_tags_count = len(raw_tags)

    pipe_eff = effective_integrator_min_score_to_pass(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )
    preview_eff = preview_effective_min_score_to_pass(repo_root, wf_sel, pasted_block)

    note = (
        "Streamlit preview uses pasted min_score_to_pass before workflow when the pasted "
        "fragment parses; pipeline emission uses env, then workflow, then thresholds.yaml only."
    )
    if preview_eff == pipe_eff:
        note = (
            "Preview and pipeline agree on min score (no pasted override, or same numeric result)."
        )

    return {
        "workflow_profile": wf_sel,
        "workflow_yaml_relpath": workflow_yaml_relpath,
        "paste_parse_errors": list(paste_errs),
        "pasted_min_score_in_fragment": (
            pasted_block.get("min_score_to_pass") if isinstance(pasted_block, dict) else None
        ),
        "thresholds_yaml": _thresholds_snapshot(repo_root, config_materializer=mat),
        "workflow_integrator_gate": {
            "block_present": wf_block is not None,
            "enabled": bool(wf_block.get("enabled")) if wf_block else None,
            "min_score_to_pass": wf_min,
            "project_tags": wf_tags,
            "project_tags_list_length": wf_project_tags_count,
        },
        "env_min_score_to_pass": _env_min_score_to_pass_breakdown(),
        "pipeline_effective_min_score_to_pass": pipe_eff,
        "streamlit_preview_effective_min_score_to_pass": preview_eff,
        "min_score_agreement_note": note,
        "gate_event_emission": _emit_integrator_gate_breakdown(
            repo_root,
            wf_sel,
            config_materializer=mat,
        ),
    }


def integrator_threshold_export_filename_slug() -> str:
    """Filename slug prefix for integrator threshold explainer exports."""
    return "integrator_threshold"


_INTEGRATOR_THRESHOLD_EXPLAINER_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def _integrator_threshold_explainer_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def integrator_threshold_explainer_table_rows(
    payload: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Sorted field/value rows for integrator threshold explainer export."""
    if not isinstance(payload, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key in sorted(str(k) for k in payload.keys()):
        rows.append(
            {
                "field": key,
                "value": _integrator_threshold_explainer_cell(payload.get(key)),
            },
        )
    return rows


def integrator_threshold_explainer_export_json(
    payload: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for integrator threshold explainer payload."""
    if not isinstance(payload, Mapping):
        return "{}"
    return json.dumps(dict(payload), indent=2, ensure_ascii=False)


def integrator_threshold_explainer_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize integrator threshold explainer field/value rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_INTEGRATOR_THRESHOLD_EXPLAINER_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _INTEGRATOR_THRESHOLD_EXPLAINER_CSV_COLUMNS},
            )
    return buf.getvalue()


_INTEGRATOR_THRESHOLD_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def integrator_threshold_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Structured rollup over :func:`integrator_threshold_explainer_payload` (§14 #13)."""
    metrics: dict[str, Any] = {
        "would_emit_gate_event": False,
        "thresholds_yaml_exists": False,
        "env_forces_on": False,
        "env_forces_off": False,
        "min_score_pipeline": None,
        "min_score_preview": None,
        "min_scores_agree": False,
        "project_tags_list_length": 0,
        "load_error_present": False,
    }
    if not isinstance(payload, Mapping):
        return metrics
    emission = payload.get("gate_event_emission")
    if isinstance(emission, Mapping):
        metrics["would_emit_gate_event"] = (
            emission.get("would_emit_integrator_gate_event") is True
        )
        metrics["thresholds_yaml_exists"] = emission.get("thresholds_yaml_exists") is True
        metrics["env_forces_on"] = emission.get("forces_on") is True
        metrics["env_forces_off"] = emission.get("forces_off") is True
    thr = payload.get("thresholds_yaml")
    if isinstance(thr, Mapping) and thr.get("exists") is True:
        metrics["thresholds_yaml_exists"] = True
    pipe = payload.get("pipeline_effective_min_score_to_pass")
    preview = payload.get("streamlit_preview_effective_min_score_to_pass")
    if isinstance(pipe, (int, float)) and not isinstance(pipe, bool):
        metrics["min_score_pipeline"] = float(pipe)
    if isinstance(preview, (int, float)) and not isinstance(preview, bool):
        metrics["min_score_preview"] = float(preview)
    if (
        metrics["min_score_pipeline"] is not None
        and metrics["min_score_preview"] is not None
    ):
        metrics["min_scores_agree"] = metrics["min_score_pipeline"] == metrics["min_score_preview"]
    wf_gate = payload.get("workflow_integrator_gate")
    if isinstance(wf_gate, Mapping):
        raw_len = wf_gate.get("project_tags_list_length")
        if isinstance(raw_len, int) and not isinstance(raw_len, bool) and raw_len >= 0:
            metrics["project_tags_list_length"] = raw_len
    paste_errs = payload.get("paste_parse_errors")
    if isinstance(paste_errs, list) and paste_errs:
        metrics["load_error_present"] = True
    return metrics


def integrator_threshold_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {
            "field": "Would emit gate event",
            "value": str(metrics.get("would_emit_gate_event", False)).lower(),
        },
        {
            "field": "Thresholds YAML exists",
            "value": str(metrics.get("thresholds_yaml_exists", False)).lower(),
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
            "field": "Min scores agree",
            "value": str(metrics.get("min_scores_agree", False)).lower(),
        },
        {
            "field": "Project tags (workflow)",
            "value": str(metrics.get("project_tags_list_length", 0)),
        },
    ]
    pipe = metrics.get("min_score_pipeline")
    if isinstance(pipe, (int, float)) and not isinstance(pipe, bool):
        rows.append({"field": "Min score pipeline", "value": str(pipe)})
    preview = metrics.get("min_score_preview")
    if isinstance(preview, (int, float)) and not isinstance(preview, bool):
        rows.append({"field": "Min score preview", "value": str(preview)})
    if metrics.get("load_error_present") is True:
        rows.append({"field": "Load error", "value": "yes"})
    return rows


def integrator_threshold_explainer_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON export of integrator threshold explainer operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def integrator_threshold_explainer_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize integrator threshold explainer operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_INTEGRATOR_THRESHOLD_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _INTEGRATOR_THRESHOLD_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def integrator_threshold_explainer_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption for threshold explainer rollup metrics."""
    if not isinstance(metrics, Mapping):
        return None
    parts: list[str] = []
    if metrics.get("would_emit_gate_event") is True:
        parts.append("gate **would emit**")
    elif metrics.get("would_emit_gate_event") is False and (
        metrics.get("thresholds_yaml_exists") is True
        or metrics.get("env_forces_off") is True
    ):
        parts.append("gate **would not emit**")
    if metrics.get("env_forces_on") is True:
        parts.append("env **forces gate on**")
    elif metrics.get("env_forces_off") is True:
        parts.append("env **forces gate off**")
    if metrics.get("min_scores_agree") is True:
        pipe = metrics.get("min_score_pipeline")
        if isinstance(pipe, (int, float)) and not isinstance(pipe, bool):
            parts.append(f"min score **{float(pipe)}** (pipeline/preview agree)")
    elif metrics.get("min_scores_agree") is False:
        pipe = metrics.get("min_score_pipeline")
        preview = metrics.get("min_score_preview")
        if isinstance(pipe, (int, float)) and isinstance(preview, (int, float)):
            parts.append(f"min score mismatch (pipeline **{pipe}**, preview **{preview}**)")
    tags_len = metrics.get("project_tags_list_length", 0)
    if isinstance(tags_len, int) and not isinstance(tags_len, bool) and tags_len > 0:
        suffix = "tag" if tags_len == 1 else "tags"
        parts.append(f"**{tags_len}** workflow project_{suffix}")
    if metrics.get("load_error_present") is True:
        parts.append("paste parse error(s)")
    if not parts:
        return None
    return "Integrator threshold explainer metrics: " + ", ".join(parts) + "."


def integrator_threshold_explainer_operator_metrics_export_filename_slug() -> str:
    """Stable slug for integrator threshold explainer operator metrics downloads."""
    return "integrator_threshold_explainer_operator_metrics"
