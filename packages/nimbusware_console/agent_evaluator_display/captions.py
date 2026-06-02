from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping
from io import StringIO
from typing import Any

from hermes_extensions.phase2 import agent_evaluator_score_band

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


def _stringify(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def agent_evaluator_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("agent_evaluator")
    return raw if isinstance(raw, dict) else None


def agent_evaluator_auto_actions_caption(ae: Mapping[str, Any] | None) -> str | None:
    if not isinstance(ae, Mapping):
        return None
    parts: list[str] = []
    promote = ae.get("auto_promote")
    if isinstance(promote, dict) and promote:
        applied = promote.get("auto_promote_probation_applied")
        if applied is True:
            parts.append("auto-promote: applied")
        elif applied is False:
            parts.append("auto-promote: skipped")
        else:
            parts.append("auto-promote: metadata present")
    create = ae.get("auto_create_persona")
    if isinstance(create, dict) and create:
        applied = create.get("auto_create_persona_applied")
        shelf = create.get("shelf")
        display = create.get("display_name")
        if applied is True:
            detail = "applied"
            if shelf is not None or display is not None:
                detail += f" (shelf={shelf!r}, display_name={display!r})"
            parts.append(f"auto-create: {detail}")
        elif applied is False:
            parts.append("auto-create: skipped")
        else:
            parts.append("auto-create: metadata present")
    if not parts:
        return None
    return "Agent evaluator actions: " + "; ".join(parts) + "."


def agent_evaluator_session_caption(ae: Mapping[str, Any] | None) -> str | None:
    if not isinstance(ae, Mapping):
        return None
    parts: list[str] = []
    pid = ae.get("persona_id")
    if isinstance(pid, str) and pid.strip():
        parts.append(f"persona_id={pid.strip()!r}")
    stage = ae.get("stage_name")
    if isinstance(stage, str) and stage.strip():
        parts.append(f"stage={stage.strip()!r}")
    attempt = ae.get("attempt")
    if isinstance(attempt, int) and not isinstance(attempt, bool):
        parts.append(f"attempt={attempt}")
    if not parts:
        return None
    return "Agent evaluator session: " + ", ".join(parts) + "."


def agent_evaluator_coverage_gate_caption(ae: Mapping[str, Any] | None) -> str | None:
    if not isinstance(ae, Mapping):
        return None
    verdict = ae.get("critique_gate_verdict")
    if not isinstance(verdict, str) or not verdict.strip():
        return None
    return f"Persona coverage critic gate: **{verdict.strip().upper()}**."


def agent_evaluator_evaluation_branch_caption(ae: Mapping[str, Any] | None) -> str | None:
    if not isinstance(ae, Mapping):
        return None
    branch = ae.get("evaluation_branch")
    if not isinstance(branch, str) or not branch.strip():
        return None
    branch_s = branch.strip()
    status = ae.get("evaluation_status")
    rules_part = (
        f"rules status={status.strip()!r}"
        if isinstance(status, str) and status.strip()
        else "rules evaluation"
    )
    if branch_s == "rules_with_llm_policy":
        llm_status = ae.get("llm_evaluation_status")
        llm_summary = ae.get("llm_evaluation_summary")
        llm_parts: list[str] = ["LLM policy branch"]
        if isinstance(llm_status, str) and llm_status.strip():
            llm_parts.append(f"policy_status={llm_status.strip()!r}")
        if isinstance(llm_summary, str) and llm_summary.strip():
            snippet = llm_summary.strip()
            if len(snippet) > 80:
                snippet = snippet[:77] + "..."
            llm_parts.append(f"summary={snippet!r}")
        llm_score = ae.get("llm_evaluation_score")
        if isinstance(llm_score, (int, float)) and not isinstance(llm_score, bool):
            llm_parts.append(f"policy_score={float(llm_score):.3f}")
            llm_band = ae.get("llm_evaluation_score_band")
            if isinstance(llm_band, str) and llm_band.strip():
                llm_parts.append(f"policy_score_band={llm_band.strip()!r}")
        return f"Agent evaluator ({rules_part}; {'; '.join(llm_parts)})."
    return f"Agent evaluator ({rules_part}; branch={branch_s!r})."


def agent_evaluator_evaluation_caption(ae: Mapping[str, Any] | None) -> str | None:
    if not isinstance(ae, Mapping):
        return None
    status = ae.get("evaluation_status")
    if not isinstance(status, str) or not status.strip():
        return None
    parts = [f"status={status.strip()!r}"]
    ba = ae.get("coverage_business_area_id")
    if isinstance(ba, str) and ba.strip():
        parts.append(f"business_area={ba.strip()!r}")
    dr = ae.get("coverage_development_role_id")
    if isinstance(dr, str) and dr.strip():
        parts.append(f"development_role={dr.strip()!r}")
    gaps = ae.get("evaluation_gaps")
    if isinstance(gaps, list):
        parts.append(f"gap_count={len(gaps)}")
    score = ae.get("evaluation_score")
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        score_f = float(score)
        parts.append(f"score={score_f:.3f}")
        band = ae.get("evaluation_score_band")
        if not isinstance(band, str) or not band.strip():
            band = agent_evaluator_score_band(score_f)
        parts.append(f"score_band={band.strip()!r}")
    cov_ratio = ae.get("coverage_ratio")
    if isinstance(cov_ratio, (int, float)) and not isinstance(cov_ratio, bool):
        parts.append(f"coverage_ratio={float(cov_ratio):.3f}")
    promotion_ready = ae.get("promotion_ready")
    if isinstance(promotion_ready, bool):
        parts.append(f"promotion_ready={promotion_ready}")
    return "Agent evaluator evaluation: " + ", ".join(parts) + "."


def agent_evaluator_auto_actions_table_rows(
    ae: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(ae, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key, label in _AUTO_ACTION_FLAT_FIELDS:
        if key not in ae:
            continue
        rows.append({"field": label, "value": _stringify(ae.get(key))})
    return rows


def agent_evaluator_summary_rows(ae: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not ae:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _AGENT_EVALUATOR_FIELDS:
        if key not in ae:
            continue
        rows.append({"field": label, "value": _stringify(ae.get(key))})
    return rows


_AGENT_EVALUATOR_TIMELINE_CSV_COLUMNS: tuple[str, ...] = ("section", "field", "value")


def agent_evaluator_timeline_export_json(ae: Mapping[str, Any] | None) -> str:
    if not isinstance(ae, Mapping):
        return "{}"
    return json.dumps(dict(ae), ensure_ascii=False, indent=2)


def agent_evaluator_timeline_table_rows_csv(ae: Mapping[str, Any] | None) -> str:
    summary = agent_evaluator_summary_rows(ae)
    auto_ = agent_evaluator_auto_actions_table_rows(ae)
    if not summary and not auto_:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_AGENT_EVALUATOR_TIMELINE_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in summary:
        w.writerow(
            {
                "section": "summary",
                "field": r.get("field", ""),
                "value": r.get("value", ""),
            },
        )
    for r in auto_:
        w.writerow(
            {
                "section": "auto_actions",
                "field": r.get("field", ""),
                "value": r.get("value", ""),
            },
        )
    return buf.getvalue()


def agent_evaluator_timeline_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]
