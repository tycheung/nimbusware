from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import as_float, as_stripped_str, is_strict_int
from console.agent_evaluator_display.captions import (
    agent_evaluator_timeline_export_filename_slug,
)
from console.explainer_core.operator_metrics_exports import (
    caption_from_parts,
    install_operator_metrics_module,
)
from console.explainer_core.schema_metrics import build_operator_metrics
from extensions.extension_runtime import agent_evaluator_score_band

_PREFIX = "agent_evaluator"

_DEFAULTS: dict[str, Any] = {
    "has_persona_id": False,
    "attempt": None,
    "evaluation_branch": None,
    "llm_evaluation_status": None,
    "evaluation_score": None,
    "evaluation_score_band": None,
    "llm_evaluation_score": None,
    "llm_evaluation_score_band": None,
    "coverage_ratio": None,
    "promotion_ready": None,
    "critique_gate_verdict": None,
    "evaluation_gaps_count": None,
    "persona_coverage_critique_branch": None,
    "rules_vs_llm_score_delta": None,
    "llm_rules_score_agreement": None,
    "auto_promote_requested": None,
    "auto_promote_applied": None,
    "auto_create_requested": None,
    "auto_create_applied": None,
    "has_auto_create_shelf": False,
}

_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("Has persona id", "has_persona_id"),
    ("Attempt", "attempt"),
    ("Rules evaluation score", "evaluation_score"),
    ("Evaluation score band", "evaluation_score_band"),
    ("LLM policy score", "llm_evaluation_score"),
    ("LLM policy score band", "llm_evaluation_score_band"),
    ("Evaluation branch", "evaluation_branch"),
    ("LLM evaluation status", "llm_evaluation_status"),
    ("Coverage ratio", "coverage_ratio"),
    ("Promotion ready", "promotion_ready"),
    ("Persona coverage gate", "critique_gate_verdict"),
    ("Evaluation gaps", "evaluation_gaps_count"),
    ("Persona coverage branch", "persona_coverage_critique_branch"),
    ("LLM − rules score delta", "rules_vs_llm_score_delta"),
    ("Rules/LLM band agreement", "llm_rules_score_agreement"),
    ("Auto-promote requested", "auto_promote_requested"),
    ("Auto-promote applied", "auto_promote_applied"),
    ("Auto-create requested", "auto_create_requested"),
    ("Auto-create applied", "auto_create_applied"),
    ("Has auto-create shelf", "has_auto_create_shelf"),
)

_SCORE_KEYS = frozenset(
    {"evaluation_score", "llm_evaluation_score", "coverage_ratio", "rules_vs_llm_score_delta"},
)


def _agent_evaluator_operator_metrics(ae: Mapping[str, Any] | None) -> dict[str, Any]:
    metrics = build_operator_metrics(
        ae,
        _DEFAULTS,
        str_present=(
            ("persona_id", "has_persona_id"),
            ("auto_create_shelf", "has_auto_create_shelf"),
        ),
        optional_int=(("attempt", "attempt"),),
        float_fields=(
            ("evaluation_score", "evaluation_score"),
            ("llm_evaluation_score", "llm_evaluation_score"),
            ("coverage_ratio", "coverage_ratio"),
        ),
        str_strip_fields=(
            ("evaluation_score_band", "evaluation_score_band"),
            ("llm_evaluation_score_band", "llm_evaluation_score_band"),
            ("evaluation_branch", "evaluation_branch"),
            ("llm_evaluation_status", "llm_evaluation_status"),
            ("persona_coverage_critique_branch", "persona_coverage_critique_branch"),
        ),
        bool_value_fields=(
            ("promotion_ready", "promotion_ready"),
            ("auto_promote_requested", "auto_promote_requested"),
            ("auto_promote_applied", "auto_promote_applied"),
            ("auto_create_requested", "auto_create_requested"),
            ("auto_create_applied", "auto_create_applied"),
        ),
        list_len_fields=(("evaluation_gaps", "evaluation_gaps_count"),),
    )
    if not isinstance(ae, Mapping):
        return metrics
    score = metrics.get("evaluation_score")
    if score is not None and metrics.get("evaluation_score_band") is None:
        metrics["evaluation_score_band"] = agent_evaluator_score_band(float(score))
    gate = as_stripped_str(ae.get("critique_gate_verdict"))
    if gate is not None:
        metrics["critique_gate_verdict"] = gate.upper()
    rules_score = metrics.get("evaluation_score")
    llm_score = metrics.get("llm_evaluation_score")
    if rules_score is not None and llm_score is not None:
        metrics["rules_vs_llm_score_delta"] = round(float(llm_score) - float(rules_score), 6)
        rules_band = metrics.get("evaluation_score_band")
        llm_band = metrics.get("llm_evaluation_score_band")
        if isinstance(rules_band, str) and isinstance(llm_band, str):
            metrics["llm_rules_score_agreement"] = rules_band.strip() == llm_band.strip()
    return metrics


def _format_metric_cell(key: str, val: object) -> str | None:
    if val is None:
        return None
    if key in _SCORE_KEYS:
        num = as_float(val)
        if num is not None:
            if key == "rules_vs_llm_score_delta":
                return f"{num:+.3f}"
            return f"{num:.3f}"
    if isinstance(val, bool):
        if key in {"has_persona_id", "has_auto_create_shelf"}:
            return "yes" if val else None
        if key in {
            "auto_promote_requested",
            "auto_promote_applied",
            "auto_create_requested",
            "auto_create_applied",
        }:
            return str(val)
        if key == "promotion_ready":
            return "yes" if val else "no"
        if key == "llm_rules_score_agreement":
            return "yes" if val else "no"
        return str(val).lower()
    if key == "attempt" and is_strict_int(val):
        return str(val)
    if key == "evaluation_gaps_count" and is_strict_int(val):
        return str(val)
    if isinstance(val, str) and val.strip():
        return val.strip()
    return None


def _agent_evaluator_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for label, key in _TABLE_ROWS:
        cell = _format_metric_cell(key, metrics.get(key))
        if cell is not None:
            rows.append({"field": label, "value": cell})
    return rows


def _caption_parts(metrics: Mapping[str, Any]) -> list[str]:
    parts: list[str] = []
    if metrics.get("has_persona_id") is True:
        parts.append("persona present")
    attempt = metrics.get("attempt")
    if is_strict_int(attempt):
        parts.append(f"attempt={attempt}")
    for key, fmt in (
        ("evaluation_score", "rules_score={:.3f}"),
        ("llm_evaluation_score", "llm_policy_score={:.3f}"),
        ("coverage_ratio", "coverage_ratio={:.3f}"),
    ):
        num = as_float(metrics.get(key))
        if num is not None:
            parts.append(fmt.format(num))
    for key, prefix in (
        ("evaluation_score_band", "score_band="),
        ("llm_evaluation_score_band", "llm_policy_score_band="),
        ("evaluation_branch", "branch="),
        ("llm_evaluation_status", "llm_status="),
        ("persona_coverage_critique_branch", "pcc_branch="),
    ):
        text = as_stripped_str(metrics.get(key))
        if text is not None:
            parts.append(f"{prefix}{text!r}")
    if metrics.get("promotion_ready") is True:
        parts.append("promotion_ready")
    gate = as_stripped_str(metrics.get("critique_gate_verdict"))
    if gate is not None:
        parts.append(f"coverage_gate={gate!r}")
    gaps_n = metrics.get("evaluation_gaps_count")
    if is_strict_int(gaps_n) and gaps_n > 0:
        parts.append(f"gap_count={gaps_n}")
    delta = as_float(metrics.get("rules_vs_llm_score_delta"))
    if delta is not None:
        parts.append(f"llm_minus_rules={delta:+.3f}")
    if metrics.get("llm_rules_score_agreement") is True:
        parts.append("bands_agree")
    elif metrics.get("llm_rules_score_agreement") is False:
        parts.append("bands_differ")
    if metrics.get("auto_promote_applied") is True:
        parts.append("auto-promote applied")
    elif metrics.get("auto_promote_applied") is False:
        parts.append("auto-promote skipped")
    if metrics.get("auto_create_applied") is True:
        parts.append("auto-create applied")
    elif metrics.get("auto_create_applied") is False:
        parts.append("auto-create skipped")
    return parts


(
    agent_evaluator_operator_metrics,
    agent_evaluator_operator_metrics_table_rows,
    agent_evaluator_operator_metrics_caption,
    agent_evaluator_operator_metrics_export_json,
    agent_evaluator_operator_metrics_table_rows_csv,
    _agent_evaluator_operator_metrics_export_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix=_PREFIX,
    metrics=_agent_evaluator_operator_metrics,
    table_rows=_agent_evaluator_operator_metrics_table_rows,
    caption=caption_from_parts("Agent evaluator metrics: ", _caption_parts),
    export_slug="agent_evaluator_operator_metrics",
)


def agent_evaluator_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return agent_evaluator_timeline_export_filename_slug(run_id, max_len=max_len)
