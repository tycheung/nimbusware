from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from nimbusware_console.components.operator_metrics import field_value_table_rows_csv
from nimbusware_extensions.phase2 import agent_evaluator_score_band

_AGENT_EVALUATOR_FIELDS: tuple[tuple[str, str], ...] = (
    ("persona_id", "Persona id"),
    ("stage_name", "Stage name"),
    ("attempt", "Attempt"),
    ("evaluation_status", "Evaluation status"),
    ("evaluation_score", "Evaluation score"),
    ("evaluation_score_band", "Evaluation score band"),
    ("llm_evaluation_score", "LLM policy score (rules anchor)"),
    ("llm_evaluation_score_band", "LLM policy score band"),
    ("coverage_ratio", "Coverage ratio"),
    ("promotion_ready", "Promotion ready"),
    ("evaluation_gaps", "Evaluation gaps"),
    ("critique_gate_verdict", "Persona coverage gate verdict"),
    ("coverage_business_area_id", "Coverage business area id"),
    ("coverage_development_role_id", "Coverage development role id"),
    ("event_id", "Event id"),
    ("occurred_at", "Occurred at"),
)

_AUTO_ACTION_FLAT_FIELDS: tuple[tuple[str, str], ...] = (
    ("auto_promote_requested", "Auto-promote requested"),
    ("auto_promote_applied", "Auto-promote applied"),
    ("auto_promote_reason", "Auto-promote reason"),
    ("auto_create_requested", "Auto-create requested"),
    ("auto_create_applied", "Auto-create applied"),
    ("auto_create_reason", "Auto-create reason"),
    ("auto_create_shelf", "Auto-create shelf"),
    ("auto_create_display_name", "Auto-create display name"),
)


from nimbusware_console.agent_evaluator_display.captions import (
    agent_evaluator_timeline_export_filename_slug,
)


def agent_evaluator_operator_metrics(
    ae: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
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
    if not isinstance(ae, Mapping):
        return metrics
    pid = ae.get("persona_id")
    if isinstance(pid, str) and pid.strip():
        metrics["has_persona_id"] = True
    attempt = ae.get("attempt")
    if isinstance(attempt, int) and not isinstance(attempt, bool):
        metrics["attempt"] = attempt
    score = ae.get("evaluation_score")
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        metrics["evaluation_score"] = float(score)
        band = ae.get("evaluation_score_band")
        if isinstance(band, str) and band.strip():
            metrics["evaluation_score_band"] = band.strip()
        else:
            metrics["evaluation_score_band"] = agent_evaluator_score_band(float(score))
    llm_score = ae.get("llm_evaluation_score")
    if isinstance(llm_score, (int, float)) and not isinstance(llm_score, bool):
        metrics["llm_evaluation_score"] = float(llm_score)
    llm_band = ae.get("llm_evaluation_score_band")
    if isinstance(llm_band, str) and llm_band.strip():
        metrics["llm_evaluation_score_band"] = llm_band.strip()
    branch = ae.get("evaluation_branch")
    if isinstance(branch, str) and branch.strip():
        metrics["evaluation_branch"] = branch.strip()
    llm_status = ae.get("llm_evaluation_status")
    if isinstance(llm_status, str) and llm_status.strip():
        metrics["llm_evaluation_status"] = llm_status.strip()
    cov_ratio = ae.get("coverage_ratio")
    if isinstance(cov_ratio, (int, float)) and not isinstance(cov_ratio, bool):
        metrics["coverage_ratio"] = float(cov_ratio)
    promotion_ready = ae.get("promotion_ready")
    if isinstance(promotion_ready, bool):
        metrics["promotion_ready"] = promotion_ready
    gate_verdict = ae.get("critique_gate_verdict")
    if isinstance(gate_verdict, str) and gate_verdict.strip():
        metrics["critique_gate_verdict"] = gate_verdict.strip().upper()
    gaps = ae.get("evaluation_gaps")
    if isinstance(gaps, list):
        metrics["evaluation_gaps_count"] = len(gaps)
    pcc_branch = ae.get("persona_coverage_critique_branch")
    if isinstance(pcc_branch, str) and pcc_branch.strip():
        metrics["persona_coverage_critique_branch"] = pcc_branch.strip()
    rules_score = metrics.get("evaluation_score")
    llm_score = metrics.get("llm_evaluation_score")
    if (
        isinstance(rules_score, (int, float))
        and not isinstance(rules_score, bool)
        and isinstance(llm_score, (int, float))
        and not isinstance(llm_score, bool)
    ):
        delta = round(float(llm_score) - float(rules_score), 6)
        metrics["rules_vs_llm_score_delta"] = delta
        rules_band = metrics.get("evaluation_score_band")
        llm_band = metrics.get("llm_evaluation_score_band")
        if (
            isinstance(rules_band, str)
            and rules_band.strip()
            and isinstance(llm_band, str)
            and llm_band.strip()
        ):
            metrics["llm_rules_score_agreement"] = rules_band.strip() == llm_band.strip()
    for key in (
        "auto_promote_requested",
        "auto_promote_applied",
        "auto_create_requested",
        "auto_create_applied",
    ):
        val = ae.get(key)
        if isinstance(val, bool):
            metrics[key] = val
    shelf = ae.get("auto_create_shelf")
    if isinstance(shelf, str) and shelf.strip():
        metrics["has_auto_create_shelf"] = True
    return metrics


def agent_evaluator_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = []
    if metrics.get("has_persona_id") is True:
        rows.append({"field": "Has persona id", "value": "yes"})
    attempt = metrics.get("attempt")
    if isinstance(attempt, int) and not isinstance(attempt, bool):
        rows.append({"field": "Attempt", "value": str(attempt)})
    rules_score = metrics.get("evaluation_score")
    if isinstance(rules_score, (int, float)) and not isinstance(rules_score, bool):
        rows.append({"field": "Rules evaluation score", "value": f"{float(rules_score):.3f}"})
    band = metrics.get("evaluation_score_band")
    if isinstance(band, str) and band.strip():
        rows.append({"field": "Evaluation score band", "value": band.strip()})
    llm_score = metrics.get("llm_evaluation_score")
    if isinstance(llm_score, (int, float)) and not isinstance(llm_score, bool):
        rows.append({"field": "LLM policy score", "value": f"{float(llm_score):.3f}"})
    llm_band = metrics.get("llm_evaluation_score_band")
    if isinstance(llm_band, str) and llm_band.strip():
        rows.append({"field": "LLM policy score band", "value": llm_band.strip()})
    branch = metrics.get("evaluation_branch")
    if isinstance(branch, str) and branch.strip():
        rows.append({"field": "Evaluation branch", "value": branch.strip()})
    llm_status = metrics.get("llm_evaluation_status")
    if isinstance(llm_status, str) and llm_status.strip():
        rows.append({"field": "LLM evaluation status", "value": llm_status.strip()})
    cov_ratio = metrics.get("coverage_ratio")
    if isinstance(cov_ratio, (int, float)) and not isinstance(cov_ratio, bool):
        rows.append({"field": "Coverage ratio", "value": f"{float(cov_ratio):.3f}"})
    if metrics.get("promotion_ready") is True:
        rows.append({"field": "Promotion ready", "value": "yes"})
    elif metrics.get("promotion_ready") is False:
        rows.append({"field": "Promotion ready", "value": "no"})
    gate_verdict = metrics.get("critique_gate_verdict")
    if isinstance(gate_verdict, str) and gate_verdict.strip():
        rows.append({"field": "Persona coverage gate", "value": gate_verdict.strip()})
    gaps_n = metrics.get("evaluation_gaps_count")
    if isinstance(gaps_n, int) and not isinstance(gaps_n, bool):
        rows.append({"field": "Evaluation gaps", "value": str(gaps_n)})
    pcc_branch = metrics.get("persona_coverage_critique_branch")
    if isinstance(pcc_branch, str) and pcc_branch.strip():
        rows.append({"field": "Persona coverage branch", "value": pcc_branch.strip()})
    delta = metrics.get("rules_vs_llm_score_delta")
    if isinstance(delta, (int, float)) and not isinstance(delta, bool):
        rows.append(
            {"field": "LLM − rules score delta", "value": f"{float(delta):+.3f}"},
        )
    if metrics.get("llm_rules_score_agreement") is True:
        rows.append({"field": "Rules/LLM band agreement", "value": "yes"})
    elif metrics.get("llm_rules_score_agreement") is False:
        rows.append({"field": "Rules/LLM band agreement", "value": "no"})
    for key, label in (
        ("auto_promote_requested", "Auto-promote requested"),
        ("auto_promote_applied", "Auto-promote applied"),
        ("auto_create_requested", "Auto-create requested"),
        ("auto_create_applied", "Auto-create applied"),
    ):
        val = metrics.get(key)
        if isinstance(val, bool):
            rows.append({"field": label, "value": str(val)})
    if metrics.get("has_auto_create_shelf") is True:
        rows.append({"field": "Has auto-create shelf", "value": "yes"})
    return rows


def agent_evaluator_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    parts: list[str] = []
    if metrics.get("has_persona_id") is True:
        parts.append("persona present")
    attempt = metrics.get("attempt")
    if isinstance(attempt, int) and not isinstance(attempt, bool):
        parts.append(f"attempt={attempt}")
    rules_score = metrics.get("evaluation_score")
    if isinstance(rules_score, (int, float)) and not isinstance(rules_score, bool):
        parts.append(f"rules_score={float(rules_score):.3f}")
    band = metrics.get("evaluation_score_band")
    if isinstance(band, str) and band.strip():
        parts.append(f"score_band={band.strip()!r}")
    llm_score = metrics.get("llm_evaluation_score")
    if isinstance(llm_score, (int, float)) and not isinstance(llm_score, bool):
        parts.append(f"llm_policy_score={float(llm_score):.3f}")
    llm_band = metrics.get("llm_evaluation_score_band")
    if isinstance(llm_band, str) and llm_band.strip():
        parts.append(f"llm_policy_score_band={llm_band.strip()!r}")
    branch = metrics.get("evaluation_branch")
    if isinstance(branch, str) and branch.strip():
        parts.append(f"branch={branch.strip()!r}")
    llm_status = metrics.get("llm_evaluation_status")
    if isinstance(llm_status, str) and llm_status.strip():
        parts.append(f"llm_status={llm_status.strip()!r}")
    cov_ratio = metrics.get("coverage_ratio")
    if isinstance(cov_ratio, (int, float)) and not isinstance(cov_ratio, bool):
        parts.append(f"coverage_ratio={float(cov_ratio):.3f}")
    if metrics.get("promotion_ready") is True:
        parts.append("promotion_ready")
    gate_verdict = metrics.get("critique_gate_verdict")
    if isinstance(gate_verdict, str) and gate_verdict.strip():
        parts.append(f"coverage_gate={gate_verdict.strip()!r}")
    gaps_n = metrics.get("evaluation_gaps_count")
    if isinstance(gaps_n, int) and not isinstance(gaps_n, bool) and gaps_n > 0:
        parts.append(f"gap_count={gaps_n}")
    pcc_branch = metrics.get("persona_coverage_critique_branch")
    if isinstance(pcc_branch, str) and pcc_branch.strip():
        parts.append(f"pcc_branch={pcc_branch.strip()!r}")
    delta = metrics.get("rules_vs_llm_score_delta")
    if isinstance(delta, (int, float)) and not isinstance(delta, bool):
        parts.append(f"llm_minus_rules={float(delta):+.3f}")
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
    if not parts:
        return None
    return "Agent evaluator metrics: " + ", ".join(parts) + "."


_AGENT_EVALUATOR_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def agent_evaluator_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


agent_evaluator_operator_metrics_table_rows_csv = field_value_table_rows_csv


def agent_evaluator_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return agent_evaluator_timeline_export_filename_slug(run_id, max_len=max_len)
