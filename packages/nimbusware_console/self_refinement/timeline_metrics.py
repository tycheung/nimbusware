from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_number, is_strict_int
from nimbusware_console.self_refinement._helpers import _parse_iso_utc
from nimbusware_console.self_refinement.latest import _TIMELINE_DESC_PREVIEW_MAX


def self_refinement_timeline_operator_metrics(
    sr: Mapping[str, Any] | None,
) -> dict[str, Any]:
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
    if is_strict_int(ungated_iters):
        out["ungated_iteration_count"] = ungated_iters
    loop_signals = sr.get("loop_signal_count")
    if is_strict_int(loop_signals) and loop_signals >= 0:
        out["loop_signal_count"] = loop_signals
    prior = sr.get("prior_gate_verdict")
    if isinstance(prior, str) and prior.strip():
        out["prior_gate_verdict"] = prior.strip()
    gate_decision = sr.get("gate_decision")
    if isinstance(gate_decision, str) and gate_decision.strip():
        out["gate_decision"] = gate_decision.strip()
    progress = sr.get("iteration_progress_ratio")
    if is_number(progress):
        out["iteration_progress_ratio"] = float(progress)
    should_continue = sr.get("should_continue")
    if isinstance(should_continue, bool):
        out["should_continue"] = should_continue
    max_iter = sr.get("max_iterations")
    if is_strict_int(max_iter) and max_iter >= 1:
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


def self_refinement_session_caption(sr: Mapping[str, Any] | None) -> str | None:
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
    window = self_refinement_marker_window_seconds(sr)
    if window is None:
        return None
    return f"Marker window: {window}s."


def self_refinement_description_length_caption(
    sr: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(sr, Mapping):
        return None
    raw = self_refinement_timeline_operator_metrics(sr).get("description_char_len")
    if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        return None
    return f"Description length: {raw} chars."


def self_refinement_markers_per_minute_caption(
    sr: Mapping[str, Any] | None,
) -> str | None:
    rate = self_refinement_markers_per_minute(sr)
    if rate is None:
        return None
    return f"Markers: {rate}/min."


def self_refinement_marker_avg_interval_caption(
    sr: Mapping[str, Any] | None,
) -> str | None:
    seconds = self_refinement_marker_avg_interval_seconds(sr)
    if seconds is None:
        return None
    return f"Markers: avg interval ~{seconds}s."


def self_refinement_marker_avg_interval_seconds(
    sr: Mapping[str, Any] | None,
) -> int | None:
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
