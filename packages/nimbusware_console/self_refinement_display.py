"""Self-refinement summary for Streamlit (plan §14 #17).

Parity with timeline top-level ``self_refinement`` from the HTTP API.
"""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from io import StringIO
from typing import Any

# Order matches ``self_refinement_timeline_summary`` in runs (human-facing first).
_SELF_REFINEMENT_FIELDS: tuple[tuple[str, str], ...] = (
    ("version", "Version"),
    ("description", "Description"),
    ("stage_name", "Stage name"),
    ("attempt", "Attempt"),
    ("gate_decision", "Gate decision"),
    ("loops_remaining", "Loops remaining"),
    ("ungated_loop", "Ungated loop"),
    ("ungated_iteration_count", "Ungated iteration count"),
    ("iteration_progress_ratio", "Iteration progress ratio"),
    ("should_continue", "Should continue"),
    ("orchestration_branch", "Orchestration branch"),
    ("max_iterations", "Max iterations"),
    ("max_iterations_exceeded", "Max iterations exceeded"),
    ("auto_promote_requested", "Auto-promote requested"),
    ("auto_promote_applied", "Auto-promote applied"),
    ("auto_promote_reason", "Auto-promote reason"),
    ("prior_gate_verdict", "Prior gate verdict"),
    ("phase_d_signal", "Phase D loop signal"),
    ("llm_critique_stage", "LLM critique panel gate"),
    ("llm_critique_summary", "LLM critique summary"),
    ("evaluation_status", "Evaluation status"),
    ("evaluation_gaps", "Evaluation gaps"),
    ("promotion_ready", "Promotion ready"),
    ("coverage_business_area_id", "Coverage business area id"),
    ("coverage_development_role_id", "Coverage development role id"),
    ("marker_count", "Marker count (session)"),
    ("first_marker_occurred_at", "First marker occurred at"),
    ("last_marker_occurred_at", "Last marker occurred at"),
    ("event_id", "Event id"),
    ("occurred_at", "Occurred at"),
)


def _stringify(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def self_refinement_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Return top-level ``self_refinement`` dict from a ``GET /v1/runs/…/timeline`` JSON body."""
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("self_refinement")
    return raw if isinstance(raw, dict) else None


def self_refinement_marker_history_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return ``self_refinement_marker_history`` list from a timeline JSON body."""
    if not isinstance(timeline_body, Mapping):
        return []
    raw = timeline_body.get("self_refinement_marker_history")
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def self_refinement_marker_history_table_rows(
    history: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Rows for ``st.dataframe`` — one row per policy marker in chronological order."""
    rows: list[dict[str, str]] = []
    for i, e in enumerate(history, start=1):
        rows.append(
            {
                "#": str(i),
                "Occurred at": _stringify(e.get("occurred_at")),
                "Version": _stringify(e.get("version")),
                "Event id": _stringify(e.get("event_id")),
            },
        )
    return rows


_SELF_REFINEMENT_MARKER_HISTORY_CSV_COLUMNS: tuple[str, ...] = (
    "#",
    "Occurred at",
    "Version",
    "Event id",
)


def self_refinement_marker_history_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize self-refinement marker history display rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SELF_REFINEMENT_MARKER_HISTORY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _SELF_REFINEMENT_MARKER_HISTORY_CSV_COLUMNS},
            )
    return buf.getvalue()


def self_refinement_marker_history_export_json(
    history: Sequence[Mapping[str, Any]],
) -> str:
    """JSON export of raw ``self_refinement_marker_history`` timeline list."""
    items = [dict(x) for x in history if isinstance(x, Mapping)]
    return json.dumps(items, ensure_ascii=False, indent=2)


def self_refinement_marker_history_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    """ASCII-ish slug for self-refinement marker history download filenames."""
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def _marker_history_window_seconds(history: list[dict[str, Any]]) -> int | None:
    """Whole-second span between first and last parseable ``occurred_at`` in history."""
    stamps: list[datetime] = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        parsed = _parse_iso_utc(entry.get("occurred_at"))
        if parsed is not None:
            stamps.append(parsed)
    if len(stamps) < 2:
        return 0 if len(stamps) == 1 else None
    lo, hi = min(stamps), max(stamps)
    delta = hi - lo
    if delta.total_seconds() < 0:
        return None
    return int(delta.total_seconds())


def self_refinement_marker_history_operator_metrics(
    history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Rollup counts for operator summary from ``self_refinement_marker_history``."""
    metrics: dict[str, Any] = {
        "entry_count": 0,
        "distinct_version_count": 0,
        "marker_window_seconds": None,
    }
    if not history:
        return metrics
    versions: set[str] = set()
    for entry in history:
        if not isinstance(entry, dict):
            continue
        metrics["entry_count"] = int(metrics["entry_count"]) + 1
        ver = entry.get("version")
        if ver is not None and str(ver).strip():
            versions.add(str(ver).strip())
    metrics["distinct_version_count"] = len(versions)
    metrics["marker_window_seconds"] = _marker_history_window_seconds(history)
    return metrics


def self_refinement_marker_history_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {"field": "Entry count", "value": str(metrics.get("entry_count", 0))},
        {
            "field": "Distinct versions",
            "value": str(metrics.get("distinct_version_count", 0)),
        },
    ]
    window = metrics.get("marker_window_seconds")
    if isinstance(window, int) and not isinstance(window, bool):
        rows.append({"field": "Marker window (s)", "value": str(window)})
    return rows


def self_refinement_marker_history_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption when marker history has at least one entry."""
    if not isinstance(metrics, Mapping):
        return None
    ec = metrics.get("entry_count")
    if isinstance(ec, bool) or not isinstance(ec, int) or ec < 1:
        return None
    parts = [f"**{ec}** marker(s)"]
    dvc = metrics.get("distinct_version_count", 0)
    if isinstance(dvc, int) and not isinstance(dvc, bool) and dvc > 0:
        parts.append(f"**{dvc}** distinct version(s)")
    window = metrics.get("marker_window_seconds")
    if isinstance(window, int) and not isinstance(window, bool) and window > 0:
        parts.append(f"**{window}**s window")
    return "Self-refinement marker history metrics: " + ", ".join(parts) + "."


_SELF_REFINEMENT_MARKER_HISTORY_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def self_refinement_marker_history_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for self-refinement marker history operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def self_refinement_marker_history_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize marker history operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SELF_REFINEMENT_MARKER_HISTORY_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _SELF_REFINEMENT_MARKER_HISTORY_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def self_refinement_marker_history_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    """ASCII-ish slug for marker history operator metrics downloads."""
    return self_refinement_marker_history_export_filename_slug(run_id, max_len=max_len)


def self_refinement_marker_history_entry_count_caption(
    history: list[dict[str, Any]] | None,
) -> str | None:
    """One-line count of policy markers in the bounded timeline history view."""
    if not history:
        return None
    n = len(history)
    word = "marker" if n == 1 else "markers"
    return f"Self-refinement marker history: **{n}** {word} in this timeline view."


def self_refinement_snapshot_from_compare_paste(
    parsed: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Normalise Module Integrator paste: full ``GET …/timeline`` body or bare ``self_refinement``.

    Full timeline bodies include ``events`` and/or top-level ``self_refinement``; bare
    pastes are the inner object only (same shape as ``self_refinement_from_timeline`` output).
    """
    if isinstance(parsed.get("events"), list) or "self_refinement" in parsed:
        return self_refinement_from_timeline(parsed)
    return dict(parsed)


def _version_as_optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def self_refinement_timeline_policy_version_caption(
    timeline_sr: Mapping[str, Any] | None,
    explainer_payload: Mapping[str, Any] | None,
) -> str | None:
    """Compare timeline marker ``version`` with disk policy and explainer merge preview."""
    if not isinstance(timeline_sr, Mapping) or not timeline_sr:
        return None
    tl_ver = _version_as_optional_int(timeline_sr.get("version"))
    if tl_ver is None:
        return None
    policy_ver: int | None = None
    merged_ver: int | None = None
    if isinstance(explainer_payload, Mapping):
        pol = explainer_payload.get("policy_yaml")
        if isinstance(pol, Mapping):
            policy_ver = _version_as_optional_int(pol.get("policy_yaml_top_level_version_int"))
            if policy_ver is None:
                policy_ver = _version_as_optional_int(pol.get("version"))
        mm = explainer_payload.get("marker_merge")
        if isinstance(mm, Mapping):
            merged_ver = _version_as_optional_int(mm.get("merged_version"))
    parts = [f"timeline={tl_ver}"]
    if policy_ver is not None:
        parts.append(f"policy file={policy_ver}")
    if merged_ver is not None:
        parts.append(f"merged preview={merged_ver}")
    refs = [v for v in (policy_ver, merged_ver) if v is not None]
    if refs and all(v == tl_ver for v in refs):
        tail = " (match)"
    elif refs and any(v != tl_ver for v in refs):
        tail = " (mismatch — see Module Integrator compare table)"
    else:
        tail = ""
    return "Self-refinement version: " + ", ".join(parts) + tail + "."


def self_refinement_policy_attempt_caption(
    timeline_sr: Mapping[str, Any] | None,
    explainer_payload: Mapping[str, Any] | None,
) -> str | None:
    """Compare timeline ``attempt`` with the pipeline marker preview (always ``1`` when enabled)."""
    if not isinstance(timeline_sr, Mapping) or not timeline_sr:
        return None
    tl_attempt = timeline_sr.get("attempt")
    if not isinstance(tl_attempt, int) or isinstance(tl_attempt, bool):
        return None
    expected: int | None = None
    if isinstance(explainer_payload, Mapping):
        mm = explainer_payload.get("marker_merge")
        if isinstance(mm, Mapping) and mm.get("would_emit_marker_after_env"):
            expected = 1
    if expected is None:
        return f"Self-refinement attempt: timeline={tl_attempt}."
    if tl_attempt == expected:
        return (
            f"Self-refinement attempt: timeline={tl_attempt}, "
            f"policy marker preview expects **{expected}** (match)."
        )
    return (
        f"Self-refinement attempt: timeline={tl_attempt}, "
        f"policy marker preview expects **{expected}** (mismatch)."
    )


def self_refinement_version_attempt_caption(
    sr: Mapping[str, Any] | None,
) -> str | None:
    """One-line ``version`` and ``attempt`` from timeline ``self_refinement``."""
    if not isinstance(sr, Mapping):
        return None
    parts: list[str] = []
    ver = sr.get("version")
    if isinstance(ver, int) and not isinstance(ver, bool):
        parts.append(f"version={ver}")
    elif ver is not None and str(ver).strip():
        parts.append(f"version={str(ver).strip()!r}")
    attempt = sr.get("attempt")
    if isinstance(attempt, int) and not isinstance(attempt, bool):
        parts.append(f"attempt={attempt}")
    if not parts:
        return None
    return "Self-refinement: " + ", ".join(parts) + "."


def self_refinement_stage_name_caption(sr: Mapping[str, Any] | None) -> str | None:
    """One-line caption when ``stage_name`` is a non-empty string on the timeline read-model."""
    if not isinstance(sr, Mapping):
        return None
    raw = sr.get("stage_name")
    if not isinstance(raw, str):
        return None
    name = raw.strip()
    if not name:
        return None
    return f"Self-refinement stage: {name}."


def self_refinement_evaluation_caption(sr: Mapping[str, Any] | None) -> str | None:
    """One-line evaluation summary from timeline ``self_refinement`` fields."""
    if not isinstance(sr, Mapping):
        return None
    status = sr.get("evaluation_status")
    if not isinstance(status, str) or not status.strip():
        return None
    parts = [f"status={status.strip()!r}"]
    ready = sr.get("promotion_ready")
    if isinstance(ready, bool):
        parts.append(f"promotion_ready={ready}")
    gaps = sr.get("evaluation_gaps")
    if isinstance(gaps, list):
        parts.append(f"gap_count={len(gaps)}")
    return "Self-refinement evaluation: " + ", ".join(parts) + "."


def self_refinement_iteration_caption(sr: Mapping[str, Any] | None) -> str | None:
    """One-line iteration summary from timeline ``self_refinement`` fields."""
    if not isinstance(sr, Mapping):
        return None
    attempt = sr.get("attempt")
    max_iter = sr.get("max_iterations")
    if not isinstance(attempt, int) or isinstance(attempt, bool):
        return None
    if isinstance(max_iter, int) and not isinstance(max_iter, bool):
        exceeded = sr.get("max_iterations_exceeded")
        if exceeded is True:
            return f"Self-refinement iteration: attempt {attempt} exceeded max {max_iter}."
        return f"Self-refinement iteration: attempt {attempt} of {max_iter}."
    return f"Self-refinement iteration: attempt {attempt}."


def self_refinement_auto_promote_caption(sr: Mapping[str, Any] | None) -> str | None:
    """One-line auto-promote summary from timeline ``self_refinement`` fields."""
    if not isinstance(sr, Mapping):
        return None
    applied = sr.get("auto_promote_applied")
    if not isinstance(applied, bool):
        promo = sr.get("auto_promote")
        if isinstance(promo, dict):
            raw = promo.get("auto_promote_probation_applied")
            applied = raw if isinstance(raw, bool) else None
    if applied is None:
        return None
    reason = sr.get("auto_promote_reason")
    if not isinstance(reason, str) or not reason.strip():
        promo = sr.get("auto_promote")
        if isinstance(promo, dict):
            raw = promo.get("reason")
            if isinstance(raw, str) and raw.strip():
                reason = raw.strip()
    if applied:
        return "Self-refinement auto-promote: applied."
    if isinstance(reason, str) and reason.strip():
        return f"Self-refinement auto-promote: not applied ({reason.strip()})."
    return "Self-refinement auto-promote: not applied."


def self_refinement_llm_critique_stage_caption(sr: Mapping[str, Any] | None) -> str | None:
    """Caption for latest ``self_refinement.critique`` gate on the timeline."""
    if not isinstance(sr, Mapping):
        return None
    raw = sr.get("llm_critique_stage")
    if not isinstance(raw, Mapping):
        return None
    verdict = raw.get("verdict")
    stage = raw.get("stage_name")
    if not isinstance(verdict, str) or not verdict.strip():
        return None
    stage_tail = ""
    if isinstance(stage, str) and stage.strip():
        stage_tail = f" ({stage.strip()})"
    return f"Self-refinement critique panel: verdict={verdict.strip()}{stage_tail}."


def self_refinement_phase_d_signal_caption(sr: Mapping[str, Any] | None) -> str | None:
    """One-line Phase D kickoff signal summary from timeline ``self_refinement``."""
    if not isinstance(sr, Mapping):
        return None
    raw = sr.get("phase_d_signal")
    if not isinstance(raw, Mapping):
        return None
    signal = raw.get("signal")
    attempt = raw.get("attempt")
    max_iterations = raw.get("max_iterations")
    gate_decision = raw.get("gate_decision")
    orchestration_branch = raw.get("orchestration_branch")
    llm_gate = raw.get("llm_gate_decision")
    if not isinstance(signal, str) or not signal.strip():
        return None
    gate_tail = ""
    if isinstance(gate_decision, str) and gate_decision.strip():
        gate_tail = f", gate={gate_decision.strip()}"
    if isinstance(llm_gate, str) and llm_gate.strip():
        gate_tail += f", llm_gate={llm_gate.strip()}"
    llm_enabled = raw.get("llm_critique_enabled")
    if isinstance(llm_enabled, bool):
        gate_tail += f", llm_critique_enabled={llm_enabled}"
    llm_attempted = raw.get("llm_critique_attempted")
    if isinstance(llm_attempted, bool):
        gate_tail += f", llm_critique_attempted={llm_attempted}"
    llm_verdict = raw.get("llm_critique_verdict")
    if isinstance(llm_verdict, str) and llm_verdict.strip():
        gate_tail += f", llm_critique_verdict={llm_verdict.strip()}"
    if isinstance(orchestration_branch, str) and orchestration_branch.strip():
        gate_tail += f", branch={orchestration_branch.strip()}"
    if isinstance(attempt, int) and isinstance(max_iterations, int):
        return (
            f"Self-refinement Phase D (rules gate): {signal.strip()} "
            f"(attempt {attempt}/{max_iterations}{gate_tail})."
        )
    return (
        f"Self-refinement Phase D (rules gate): {signal.strip()}{gate_tail}."
    )


def self_refinement_prior_gate_verdict_caption(sr: Mapping[str, Any] | None) -> str | None:
    """One-line caption for rules-gate verdict that preceded the latest SR marker."""
    if not isinstance(sr, Mapping):
        return None
    verdict = sr.get("prior_gate_verdict")
    if not isinstance(verdict, str) or not verdict.strip():
        return None
    return f"Self-refinement prior gate verdict: **{verdict.strip().upper()}**."


def self_refinement_ungated_loop_caption(sr: Mapping[str, Any] | None) -> str | None:
    """One-line caption for ungated-loop progression fields from timeline summary."""
    if not isinstance(sr, Mapping):
        return None
    ungated = sr.get("ungated_loop")
    if not isinstance(ungated, bool):
        return None
    gate = sr.get("gate_decision")
    loops_remaining = sr.get("loops_remaining")
    progress_ratio = sr.get("iteration_progress_ratio")
    should_continue = sr.get("should_continue")
    parts = [f"ungated_loop={ungated}"]
    loop_signals = sr.get("loop_signal_count")
    if isinstance(loop_signals, int) and not isinstance(loop_signals, bool):
        parts.append(f"loop_signal_count={loop_signals}")
    ungated_iters = sr.get("ungated_iteration_count")
    if isinstance(ungated_iters, int) and not isinstance(ungated_iters, bool):
        parts.append(f"ungated_iteration_count={ungated_iters}")
    if isinstance(gate, str) and gate.strip():
        parts.append(f"gate={gate.strip()}")
    if isinstance(loops_remaining, int) and not isinstance(loops_remaining, bool):
        parts.append(f"loops_remaining={loops_remaining}")
    if isinstance(progress_ratio, (int, float)) and not isinstance(progress_ratio, bool):
        parts.append(f"progress_ratio={float(progress_ratio):.3f}")
    if isinstance(should_continue, bool):
        parts.append(f"should_continue={should_continue}")
    return "Self-refinement ungated progression: " + ", ".join(parts) + "."


def self_refinement_summary_rows(sr: Mapping[str, Any] | None) -> list[dict[str, str]]:
    """Rows suitable for ``st.dataframe`` (field / value columns)."""
    if not sr:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _SELF_REFINEMENT_FIELDS:
        if key not in sr:
            continue
        rows.append({"field": label, "value": _stringify(sr.get(key))})
    return rows


_SELF_REFINEMENT_LATEST_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def self_refinement_latest_summary_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    """Serialize latest self-refinement summary rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SELF_REFINEMENT_LATEST_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _SELF_REFINEMENT_LATEST_SUMMARY_CSV_COLUMNS},
            )
    return buf.getvalue()


def self_refinement_latest_export_json(sr: Mapping[str, Any] | None) -> str:
    """JSON export of timeline top-level ``self_refinement`` summary."""
    if not isinstance(sr, Mapping):
        return "{}"
    return json.dumps(dict(sr), ensure_ascii=False, indent=2)


def self_refinement_latest_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    """ASCII-ish slug for latest self-refinement summary download filenames."""
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def self_refinement_timeline_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for self-refinement timeline operator metrics."""
    if not isinstance(metrics, Mapping) or not metrics.get("present"):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def self_refinement_timeline_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize self-refinement timeline operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SELF_REFINEMENT_LATEST_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _SELF_REFINEMENT_LATEST_SUMMARY_CSV_COLUMNS},
            )
    return buf.getvalue()


def self_refinement_timeline_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    """ASCII-ish slug for self-refinement timeline operator metrics downloads."""
    return self_refinement_latest_export_filename_slug(run_id, max_len=max_len)


_TIMELINE_DESC_PREVIEW_MAX = 240


def self_refinement_timeline_operator_metrics(
    sr: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Read-only drill-down on timeline ``self_refinement`` (length + preview, version hints)."""
    if not sr:
        return {"present": False}
    desc = sr.get("description")
    dlen = 0
    dprev: str | None = None
    if isinstance(desc, str):
        dlen = len(desc)
        if desc:
            if len(desc) > _TIMELINE_DESC_PREVIEW_MAX:
                dprev = desc[:_TIMELINE_DESC_PREVIEW_MAX] + "..."
            else:
                dprev = desc
    elif desc is not None:
        s = str(desc)
        dlen = len(s)
        tail = "..." if len(s) > _TIMELINE_DESC_PREVIEW_MAX else ""
        dprev = s[:_TIMELINE_DESC_PREVIEW_MAX] + tail

    ver = sr.get("version")
    ver_int: int | None = None
    if isinstance(ver, int):
        ver_int = ver
    elif isinstance(ver, str) and ver.strip().isdigit():
        ver_int = int(ver.strip())

    out: dict[str, Any] = {
        "present": True,
        "description_char_len": dlen,
        "description_preview": dprev,
        "version_raw_type": type(ver).__name__ if ver is not None else None,
    }
    if ver_int is not None:
        out["version_as_int"] = ver_int
    att = sr.get("attempt")
    if att is not None:
        out["attempt_raw"] = att
    mc = sr.get("marker_count")
    if isinstance(mc, int) and mc >= 0:
        out["marker_count"] = mc
    window = self_refinement_marker_window_seconds(sr)
    if window is not None:
        out["marker_window_seconds"] = window
    avg = self_refinement_marker_avg_interval_seconds(sr)
    if avg is not None:
        out["marker_avg_interval_seconds"] = avg
    mpm = self_refinement_markers_per_minute(sr)
    if mpm is not None:
        out["markers_per_minute"] = mpm
    ungated = sr.get("ungated_loop")
    if isinstance(ungated, bool):
        out["ungated_loop"] = ungated
    ungated_iters = sr.get("ungated_iteration_count")
    if isinstance(ungated_iters, int) and not isinstance(ungated_iters, bool):
        out["ungated_iteration_count"] = ungated_iters
    loop_signals = sr.get("loop_signal_count")
    if isinstance(loop_signals, int) and not isinstance(loop_signals, bool) and loop_signals >= 0:
        out["loop_signal_count"] = loop_signals
    prior = sr.get("prior_gate_verdict")
    if isinstance(prior, str) and prior.strip():
        out["prior_gate_verdict"] = prior.strip()
    gate_decision = sr.get("gate_decision")
    if isinstance(gate_decision, str) and gate_decision.strip():
        out["gate_decision"] = gate_decision.strip()
    progress = sr.get("iteration_progress_ratio")
    if isinstance(progress, (int, float)) and not isinstance(progress, bool):
        out["iteration_progress_ratio"] = float(progress)
    should_continue = sr.get("should_continue")
    if isinstance(should_continue, bool):
        out["should_continue"] = should_continue
    max_iter = sr.get("max_iterations")
    if isinstance(max_iter, int) and not isinstance(max_iter, bool) and max_iter >= 1:
        out["max_iterations"] = max_iter
    max_exceeded = sr.get("max_iterations_exceeded")
    if isinstance(max_exceeded, bool):
        out["max_iterations_exceeded"] = max_exceeded
    llm_summary = sr.get("llm_critique_summary")
    if isinstance(llm_summary, str) and llm_summary.strip():
        preview = llm_summary.strip()
        if len(preview) > _TIMELINE_DESC_PREVIEW_MAX:
            preview = preview[:_TIMELINE_DESC_PREVIEW_MAX] + "..."
        out["llm_critique_summary_preview"] = preview
    return out


def _parse_iso_utc(value: Any) -> datetime | None:
    """Parse an ISO 8601 timestamp written by the API; ``Z`` suffix is accepted."""
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def self_refinement_session_caption(sr: Mapping[str, Any] | None) -> str | None:
    """One-line operator caption rolling marker count + window + average together.

    Reads only the existing timeline fields (no new operator-metric keys). Returns:

    * ``"Self-refinement: <N> markers across <W>s (avg <A>s)."`` when ``marker_count >= 2``
      and ``self_refinement_marker_window_seconds`` is observable (the average uses
      :func:`self_refinement_marker_avg_interval_seconds` for parity with the table row),
    * ``"Self-refinement: single marker."`` when ``marker_count == 1``,
    * ``None`` when ``sr`` is not a mapping, ``marker_count`` is absent / not a
      non-negative integer (booleans excluded since :class:`bool` subclasses
      :class:`int`), ``marker_count == 0``, or the window / average is unobservable for
      the multi-marker case.
    """
    if not isinstance(sr, Mapping):
        return None
    mc = sr.get("marker_count")
    if isinstance(mc, bool) or not isinstance(mc, int) or mc < 1:
        return None
    if mc == 1:
        return "Self-refinement: single marker."
    window = self_refinement_marker_window_seconds(sr)
    avg = self_refinement_marker_avg_interval_seconds(sr)
    if window is None or avg is None:
        return None
    return f"Self-refinement: {mc} markers across {window}s (avg {avg}s)."


def self_refinement_markers_per_minute(sr: Mapping[str, Any] | None) -> int | None:
    """Marker throughput rounded to whole markers per minute.

    Computed as ``round(marker_count * 60 / marker_window_seconds)`` so that a session
    with two markers exactly thirty seconds apart yields ``4`` (two markers extrapolated
    over a one-minute window). Returns ``None`` when:

    * ``sr`` is not a mapping, **or**
    * ``self_refinement_marker_window_seconds`` returns ``None`` or ``0`` (single marker
      runs have no observable rate even though the window is technically zero), **or**
    * ``marker_count`` is absent / not a non-negative integer (booleans are excluded
      since :class:`bool` is a subclass of :class:`int`), **or**
    * ``marker_count`` is less than ``2`` (no observable rate over the window).
    """
    if not isinstance(sr, Mapping):
        return None
    mc = sr.get("marker_count")
    if isinstance(mc, bool) or not isinstance(mc, int) or mc < 2:
        return None
    window = self_refinement_marker_window_seconds(sr)
    if window is None or window <= 0:
        return None
    return int(round(mc * 60 / window))


def self_refinement_marker_first_last_caption(
    sr: Mapping[str, Any] | None,
) -> str | None:
    """One-line caption quoting the first and last marker ISO timestamps.

    Reuses :func:`_parse_iso_utc` so the same ``Z``-suffix handling applies. Returns:

    * ``"Markers: first <iso>, last <iso>."`` when both ``first_marker_occurred_at`` and
      ``last_marker_occurred_at`` parse and the timestamps differ,
    * ``"Markers: single at <iso>."`` when both parse and the timestamps are equal
      (single-marker session collapsed into one ISO string),
    * ``None`` when ``sr`` is not a mapping, either timestamp is missing or
      unparseable, or the values cannot be normalised against each other.

    The emitted ISO strings are the raw, whitespace-stripped originals from ``sr`` (so
    the operator sees the exact wire-format the API emitted), not re-serialised from
    the parsed :class:`datetime` value.
    """
    if not isinstance(sr, Mapping):
        return None
    first_raw = sr.get("first_marker_occurred_at")
    last_raw = sr.get("last_marker_occurred_at")
    first_dt = _parse_iso_utc(first_raw)
    last_dt = _parse_iso_utc(last_raw)
    if first_dt is None or last_dt is None:
        return None
    first_str = str(first_raw).strip() if isinstance(first_raw, str) else ""
    last_str = str(last_raw).strip() if isinstance(last_raw, str) else ""
    if not first_str or not last_str:
        return None
    if first_dt == last_dt:
        return f"Markers: single at {first_str}."
    return f"Markers: first {first_str}, last {last_str}."


def self_refinement_marker_window_caption(
    sr: Mapping[str, Any] | None,
) -> str | None:
    """Caption form of :func:`self_refinement_marker_window_seconds`.

    Returns ``"Marker window: <N>s."`` when the underlying numeric helper yields a
    non-negative integer; ``None`` whenever the helper returns ``None``. Mirrors
    the caption-wrapper pattern of ``self_refinement_marker_avg_interval_caption``
    / ``self_refinement_markers_per_minute_caption``.
    """
    window = self_refinement_marker_window_seconds(sr)
    if window is None:
        return None
    return f"Marker window: {window}s."


def self_refinement_description_length_caption(
    sr: Mapping[str, Any] | None,
) -> str | None:
    """One-line caption from ``description_char_len`` in operator metrics.

    Sources :func:`self_refinement_timeline_operator_metrics` so the rule for
    description length stays in one place. Returns ``"Description length: <N> chars."``
    when the metric is a positive ``int`` (``bool`` excluded since :class:`bool` subclasses
    :class:`int`). Returns ``None`` for non-mapping ``sr``, missing / non-positive /
    non-integer ``description_char_len``, or zero length (missing / empty description).
    """
    if not isinstance(sr, Mapping):
        return None
    raw = self_refinement_timeline_operator_metrics(sr).get("description_char_len")
    if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        return None
    return f"Description length: {raw} chars."


def self_refinement_markers_per_minute_caption(
    sr: Mapping[str, Any] | None,
) -> str | None:
    """Caption form of :func:`self_refinement_markers_per_minute`.

    Returns ``"Markers: <N>/min."`` when the underlying numeric helper yields a
    non-negative integer (mirrors the caption pattern used by
    ``self_refinement_session_caption`` / ``self_refinement_marker_first_last_caption`` /
    ``self_refinement_marker_avg_interval_caption``). Returns ``None`` whenever the
    helper returns ``None`` (non-mapping input, missing window, missing / non-int /
    boolean ``marker_count``, ``marker_count < 2``, zero window).
    """
    rate = self_refinement_markers_per_minute(sr)
    if rate is None:
        return None
    return f"Markers: {rate}/min."


def self_refinement_marker_avg_interval_caption(
    sr: Mapping[str, Any] | None,
) -> str | None:
    """Caption form of :func:`self_refinement_marker_avg_interval_seconds`.

    Returns ``"Markers: avg interval ~<N>s."`` when the underlying numeric helper
    yields a non-negative integer (mirrors the caption pattern used by
    ``self_refinement_session_caption`` and ``self_refinement_marker_first_last_caption``).
    Returns ``None`` whenever the helper returns ``None`` (non-mapping input, missing /
    unparseable timestamps, missing / non-int / boolean ``marker_count``, or
    ``marker_count < 2``).
    """
    seconds = self_refinement_marker_avg_interval_seconds(sr)
    if seconds is None:
        return None
    return f"Markers: avg interval ~{seconds}s."


def self_refinement_marker_avg_interval_seconds(
    sr: Mapping[str, Any] | None,
) -> int | None:
    """Average seconds between adjacent self-refinement markers in a session.

    Computed as ``marker_window_seconds / (marker_count - 1)`` rounded to the nearest
    integer second. Returns ``None`` when:

    * ``sr`` is not a mapping, **or**
    * ``self_refinement_marker_window_seconds`` returns ``None`` (missing / unparseable
      first / last timestamps, clock skew), **or**
    * ``marker_count`` is absent or not a non-negative integer (booleans are excluded
      since :class:`bool` is a subclass of :class:`int`), **or**
    * ``marker_count`` is less than ``2`` (no interval to average over).
    """
    if not isinstance(sr, Mapping):
        return None
    window = self_refinement_marker_window_seconds(sr)
    if window is None:
        return None
    mc = sr.get("marker_count")
    if isinstance(mc, bool) or not isinstance(mc, int) or mc < 2:
        return None
    return int(round(window / (mc - 1)))


def self_refinement_marker_window_seconds(sr: Mapping[str, Any] | None) -> int | None:
    """Whole-seconds delta between ``first_marker_occurred_at`` and ``last_marker_occurred_at``.

    Returns ``None`` when either timestamp is absent or not a parseable ISO 8601 UTC string.
    A single-marker run (first == last) returns ``0``. The window is rounded to the nearest
    integer second; negative deltas (clock skew) collapse to ``None``.
    """
    if not isinstance(sr, Mapping):
        return None
    first = _parse_iso_utc(sr.get("first_marker_occurred_at"))
    last = _parse_iso_utc(sr.get("last_marker_occurred_at"))
    if first is None or last is None:
        return None
    delta = (last - first).total_seconds()
    if delta < 0:
        return None
    return int(round(delta))


def self_refinement_timeline_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not metrics or not metrics.get("present"):
        return []
    rows: list[dict[str, str]] = []
    rows.append(
        {
            "field": "Description length (chars)",
            "value": str(metrics.get("description_char_len", 0)),
        },
    )
    dp = metrics.get("description_preview")
    if dp:
        rows.append({"field": "Description preview", "value": str(dp)})
    vrt = metrics.get("version_raw_type")
    if vrt:
        rows.append({"field": "Version JSON type", "value": str(vrt)})
    if "version_as_int" in metrics:
        rows.append(
            {
                "field": "Version (integer parse when digits-only)",
                "value": str(metrics["version_as_int"]),
            },
        )
    if "attempt_raw" in metrics:
        rows.append({"field": "Attempt (raw)", "value": str(metrics["attempt_raw"])})
    if "marker_count" in metrics:
        rows.append(
            {"field": "Self-refinement markers (session)", "value": str(metrics["marker_count"])},
        )
    if "ungated_loop" in metrics:
        rows.append(
            {"field": "Ungated loop", "value": str(metrics["ungated_loop"])},
        )
    if "ungated_iteration_count" in metrics:
        rows.append(
            {
                "field": "Ungated iteration count",
                "value": str(metrics["ungated_iteration_count"]),
            },
        )
    if "loop_signal_count" in metrics:
        rows.append(
            {
                "field": "Loop signal count",
                "value": str(metrics["loop_signal_count"]),
            },
        )
    if "prior_gate_verdict" in metrics:
        rows.append(
            {
                "field": "Prior gate verdict",
                "value": str(metrics["prior_gate_verdict"]),
            },
        )
    if "gate_decision" in metrics:
        rows.append({"field": "Gate decision", "value": str(metrics["gate_decision"])})
    if "iteration_progress_ratio" in metrics:
        rows.append(
            {
                "field": "Iteration progress ratio",
                "value": f"{float(metrics['iteration_progress_ratio']):.3f}",
            },
        )
    if "should_continue" in metrics:
        rows.append(
            {"field": "Should continue", "value": str(metrics["should_continue"])},
        )
    if "max_iterations" in metrics:
        rows.append(
            {"field": "Max iterations", "value": str(metrics["max_iterations"])},
        )
    if "max_iterations_exceeded" in metrics:
        rows.append(
            {
                "field": "Max iterations exceeded",
                "value": str(metrics["max_iterations_exceeded"]),
            },
        )
    llm_prev = metrics.get("llm_critique_summary_preview")
    if isinstance(llm_prev, str) and llm_prev.strip():
        rows.append(
            {"field": "LLM critique summary (preview)", "value": llm_prev.strip()},
        )
    if "marker_window_seconds" in metrics:
        rows.append(
            {
                "field": "Marker window (s)",
                "value": str(metrics["marker_window_seconds"]),
            },
        )
    if "marker_avg_interval_seconds" in metrics:
        rows.append(
            {
                "field": "Marker average interval (s)",
                "value": str(metrics["marker_avg_interval_seconds"]),
            },
        )
    if "markers_per_minute" in metrics:
        rows.append(
            {
                "field": "Markers per minute",
                "value": str(metrics["markers_per_minute"]),
            },
        )
    return rows
