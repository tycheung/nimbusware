from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def integrator_threshold_gate_emission_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
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
    return f"Integrator threshold: pasted gate YAML has **{n}** parse {word}: {body}."


def integrator_threshold_project_tags_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
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
