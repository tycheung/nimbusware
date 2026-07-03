from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_number, is_strict_int
from console.self_refinement.marker_history import self_refinement_from_timeline


def self_refinement_snapshot_from_compare_paste(
    parsed: Mapping[str, Any],
) -> dict[str, Any] | None:
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
    if not isinstance(sr, Mapping):
        return None
    parts: list[str] = []
    ver = sr.get("version")
    if is_strict_int(ver):
        parts.append(f"version={ver}")
    elif ver is not None and str(ver).strip():
        parts.append(f"version={str(ver).strip()!r}")
    attempt = sr.get("attempt")
    if is_strict_int(attempt):
        parts.append(f"attempt={attempt}")
    if not parts:
        return None
    return "Self-refinement: " + ", ".join(parts) + "."


def self_refinement_stage_name_caption(sr: Mapping[str, Any] | None) -> str | None:
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
    if not isinstance(sr, Mapping):
        return None
    attempt = sr.get("attempt")
    max_iter = sr.get("max_iterations")
    if not isinstance(attempt, int) or isinstance(attempt, bool):
        return None
    if is_strict_int(max_iter):
        exceeded = sr.get("max_iterations_exceeded")
        if exceeded is True:
            return f"Self-refinement iteration: attempt {attempt} exceeded max {max_iter}."
        return f"Self-refinement iteration: attempt {attempt} of {max_iter}."
    return f"Self-refinement iteration: attempt {attempt}."


def self_refinement_auto_promote_caption(sr: Mapping[str, Any] | None) -> str | None:
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
    return f"Self-refinement Phase D (rules gate): {signal.strip()}{gate_tail}."


def self_refinement_prior_gate_verdict_caption(sr: Mapping[str, Any] | None) -> str | None:
    if not isinstance(sr, Mapping):
        return None
    verdict = sr.get("prior_gate_verdict")
    if not isinstance(verdict, str) or not verdict.strip():
        return None
    return f"Self-refinement prior gate verdict: **{verdict.strip().upper()}**."


def self_refinement_ungated_loop_caption(sr: Mapping[str, Any] | None) -> str | None:
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
    if is_strict_int(loop_signals):
        parts.append(f"loop_signal_count={loop_signals}")
    ungated_iters = sr.get("ungated_iteration_count")
    if is_strict_int(ungated_iters):
        parts.append(f"ungated_iteration_count={ungated_iters}")
    if isinstance(gate, str) and gate.strip():
        parts.append(f"gate={gate.strip()}")
    if is_strict_int(loops_remaining):
        parts.append(f"loops_remaining={loops_remaining}")
    if is_number(progress_ratio):
        parts.append(f"progress_ratio={float(progress_ratio):.3f}")
    if isinstance(should_continue, bool):
        parts.append(f"should_continue={should_continue}")
    return "Self-refinement ungated progression: " + ", ".join(parts) + "."
