from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from nimbusware_console.run_escalated._common import _stringify


def run_escalated_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    sev = metrics.get("severity")
    if isinstance(sev, str) and sev.strip():
        return f"Run escalated: severity **{sev.strip()}**."
    present: list[str] = []
    if metrics.get("reason_code_present") is True:
        present.append("reason code")
    if metrics.get("actor_id_present") is True:
        present.append("actor")
    if metrics.get("policy_snapshot_id_present") is True:
        present.append("policy snapshot")
    if metrics.get("event_id_present") is True:
        present.append("event id")
    if metrics.get("notes_present") is True:
        present.append("notes")
    if not present:
        return None
    return "Run escalated metrics: " + ", ".join(present) + " present."


_RUN_ESCALATED_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = ("field", "value")




def run_escalated_occurred_at_caption(summary: Mapping[str, Any] | None) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    raw = summary.get("occurred_at")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Run escalated at: {text}."




def run_escalated_event_id_caption(summary: Mapping[str, Any] | None) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    raw = summary.get("event_id")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Run escalated event_id: `{text}`."




def run_escalated_reason_summary_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(summary, Mapping) or not summary:
        return None
    parts: list[str] = []
    rc = summary.get("reason_code")
    if rc is not None and str(rc).strip():
        parts.append(f"reason_code={str(rc).strip()}")
    actor = summary.get("actor_id")
    if isinstance(actor, str) and actor.strip():
        parts.append(f"actor_id={actor.strip()}")
    pol = summary.get("policy_snapshot_id")
    if pol is not None and str(pol).strip():
        parts.append(f"policy_snapshot_id={str(pol).strip()}")
    if not parts:
        return None
    return "Run escalated: " + ", ".join(parts) + "."




def run_escalated_notes_preview_caption(
    summary: Mapping[str, Any] | None,
    *,
    max_len: int = 120,
) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    notes = summary.get("notes")
    if not isinstance(notes, str):
        return None
    text = notes.strip()
    if not text:
        return None
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return f"Escalation notes: {text!r}."




def run_escalated_actor_without_notes_caption(summary: Mapping[str, Any] | None) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    raw_actor = summary.get("actor_id")
    if not isinstance(raw_actor, str) or not raw_actor.strip():
        return None
    notes = summary.get("notes")
    if isinstance(notes, str) and notes.strip():
        return None
    if notes is not None and not isinstance(notes, str):
        return None
    return (
        "Escalation **actor_id** is set but **notes** are empty — add operator context when "
        "correlating this **run.escalated** event with ``configs/escalation/policy.yaml``."
    )




def run_escalated_policy_cross_ref_caption(
    repo_root: Path | None,
    summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    raw = summary.get("policy_snapshot_id")
    if raw is None:
        return None
    sid = str(raw).strip()
    if not sid:
        return None
    rel = "configs/escalation/policy.yaml"
    tail = (
        f"Thresholds and counters are defined under ``{rel}`` (repo-relative). "
        "Compare **Escalation suppress (workflow + parsed)** under Module Integrator for "
        "``suppress_automatic_escalation`` vs automatic ``run.escalated`` emitters."
    )
    if repo_root is None:
        return f"**policy_snapshot_id:** ``{sid}``. {tail}"
    pol = repo_root / "configs" / "escalation" / "policy.yaml"
    if pol.is_file():
        on_disk = "policy file present on this repo root"
    else:
        on_disk = "policy file missing on this repo root"
    return f"**policy_snapshot_id:** ``{sid}`` ({on_disk}). {tail}"




def run_escalated_history_entry_count_caption(
    history: list[dict[str, Any]] | None,
) -> str | None:
    if not history:
        return None
    n = len(history)
    word = "escalation" if n == 1 else "escalations"
    return f"Run escalated history: **{n}** {word} in this timeline view."




def run_escalated_history_distinct_actors_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    ec = metrics.get("entry_count")
    if isinstance(ec, bool) or not isinstance(ec, int) or ec < 1:
        return None
    dac = metrics.get("distinct_actor_ids")
    if not isinstance(dac, int) or isinstance(dac, bool) or dac < 0:
        return None
    if dac == 0:
        return "Run escalated history: no distinct actor ids in this view."
    word = "actor" if dac == 1 else "actors"
    return f"Run escalated history: **{dac}** distinct {word} across **{ec}** escalation(s)."




def run_escalated_history_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    ec = metrics.get("entry_count")
    if isinstance(ec, bool) or not isinstance(ec, int) or ec < 1:
        return None
    parts = [f"**{ec}** escalation(s)"]
    drc = metrics.get("distinct_reason_codes", 0)
    if isinstance(drc, int) and not isinstance(drc, bool) and drc > 0:
        parts.append(f"**{drc}** distinct reason code(s)")
    npc = metrics.get("notes_present_count", 0)
    if isinstance(npc, int) and not isinstance(npc, bool) and npc > 0:
        parts.append(f"**{npc}** with notes")
    dac = metrics.get("distinct_actor_ids", 0)
    if isinstance(dac, int) and not isinstance(dac, bool) and dac > 0:
        word = "actor" if dac == 1 else "actors"
        parts.append(f"**{dac}** distinct {word}")
    return "Run escalated history metrics: " + ", ".join(parts) + "."


_RUN_ESCALATED_HISTORY_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)




def run_escalated_delta_transition_caption(
    delta: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(delta, Mapping):
        return None
    parts: list[str] = []
    if delta.get("reason_code_changed") is True:
        prev = _stringify(delta.get("previous_reason_code"))
        cur = _stringify(delta.get("current_reason_code"))
        parts.append(f"reason {prev} → {cur}")
    if delta.get("actor_id_changed") is True:
        prev_a = _stringify(delta.get("previous_actor_id"))
        cur_a = _stringify(delta.get("current_actor_id"))
        parts.append(f"actor {prev_a} → {cur_a}")
    if delta.get("policy_snapshot_id_changed") is True:
        parts.append("policy_snapshot_id changed")
    if not parts:
        return None
    return "Run escalated delta: " + "; ".join(parts) + "."




def run_escalated_delta_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping) or not metrics.get("present"):
        return None
    changed: list[str] = []
    for key, label in (
        ("reason_code_changed", "reason code"),
        ("actor_id_changed", "actor id"),
        ("policy_snapshot_id_changed", "policy snapshot id"),
    ):
        if metrics.get(key) is True:
            changed.append(label)
    if not changed:
        stable: list[str] = []
        if metrics.get("has_previous") is True and metrics.get("has_current") is True:
            stable.append("previous and current events present")
        elif metrics.get("has_current") is True:
            stable.append("current event only")
        if not stable:
            return None
        return "Run escalated delta metrics: no field changes (" + ", ".join(stable) + ")."
    return "Run escalated delta metrics: changed " + ", ".join(changed) + "."


_RUN_ESCALATED_DELTA_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


