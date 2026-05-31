from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.integrator_gate._helpers import (
    _optional_float,
)


def integrator_gate_delta_operator_metrics(
    delta: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not delta:
        return {"present": False}
    sd = _optional_float(delta.get("integrator_score_delta"))
    direction: str | None = None
    if sd is not None:
        if sd > 1e-9:
            direction = "up"
        elif sd < -1e-9:
            direction = "down"
        else:
            direction = "flat"
    pv = delta.get("previous_verdict")
    cv = delta.get("current_verdict")
    flip = None
    if pv is not None or cv is not None:
        flip = f"{pv!s} -> {cv!s}"
    return {
        "present": True,
        "score_delta_direction": direction,
        "integrator_score_delta": sd,
        "verdict_changed": bool(delta.get("verdict_changed"))
        if "verdict_changed" in delta
        else None,
        "bundle_id_changed": bool(delta.get("bundle_id_changed"))
        if "bundle_id_changed" in delta
        else None,
        "verdict_transition": flip,
    }


def integrator_gate_delta_bundle_changed_caption(
    delta: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(delta, Mapping):
        return None
    raw = delta.get("bundle_id_changed")
    if isinstance(raw, bool):
        return f"Integrator gate delta: bundle_id_changed **{str(raw).lower()}**."
    return None


def integrator_gate_delta_verdict_changed_caption(
    delta: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(delta, Mapping):
        return None
    raw = delta.get("verdict_changed")
    if isinstance(raw, bool):
        return f"Integrator gate delta: verdict_changed **{str(raw).lower()}**."
    return None


def integrator_gate_delta_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping) or metrics.get("present") is not True:
        return None
    parts: list[str] = []
    vt = metrics.get("verdict_transition")
    if isinstance(vt, str) and vt.strip():
        parts.append(f"verdict {vt}")
    direction = metrics.get("score_delta_direction")
    sd = metrics.get("integrator_score_delta")
    if direction is not None and sd is not None:
        parts.append(f"score {direction} ({sd:+.6g})")
    elif direction is not None:
        parts.append(f"score {direction}")
    if metrics.get("bundle_id_changed") is True:
        parts.append("bundle id changed")
    if not parts:
        return (
            "Integrator gate delta operator metrics: present "
            "(no score or verdict transition to summarize)."
        )
    return "Integrator gate delta operator metrics: " + "; ".join(parts) + "."


def integrator_gate_delta_transition_caption(
    delta: Mapping[str, Any] | None,
) -> str | None:
    return integrator_gate_delta_operator_metrics_caption(
        integrator_gate_delta_operator_metrics(delta),
    )


def integrator_gate_delta_operator_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not metrics or not metrics.get("present"):
        return []
    rows: list[dict[str, str]] = []
    if metrics.get("score_delta_direction") is not None:
        rows.append(
            {
                "field": "Score delta direction",
                "value": str(metrics["score_delta_direction"]),
            },
        )
    if metrics.get("integrator_score_delta") is not None:
        rows.append(
            {
                "field": "Score delta (raw)",
                "value": str(metrics["integrator_score_delta"]),
            },
        )
    if metrics.get("verdict_changed") is not None:
        rows.append(
            {
                "field": "Verdict changed",
                "value": str(metrics["verdict_changed"]),
            },
        )
    if metrics.get("bundle_id_changed") is not None:
        rows.append(
            {
                "field": "Bundle id changed",
                "value": str(metrics["bundle_id_changed"]),
            },
        )
    vt = metrics.get("verdict_transition")
    if vt:
        rows.append({"field": "Verdict transition", "value": str(vt)})
    return rows
