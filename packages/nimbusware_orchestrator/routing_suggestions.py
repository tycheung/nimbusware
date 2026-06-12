from __future__ import annotations

from typing import Any


def _nested_get(doc: dict[str, Any], path: tuple[str, ...]) -> Any:
    cur: Any = doc
    for part in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def suggest_model_routing_changes(
    aggregate: dict[str, Any],
    routing: dict[str, Any],
    *,
    fallback_rate_threshold: float = 0.25,
    latency_headroom_ratio: float = 0.8,
) -> list[dict[str, Any]]:
    """Propose ``model-routing.yaml`` tweaks; operator applies via ``nimbusware-config``."""
    suggestions: list[dict[str, Any]] = []
    preflight = aggregate.get("preflight")
    if isinstance(preflight, dict):
        observed_p95 = preflight.get("max_p95_latency_ms")
        if isinstance(observed_p95, (int, float)):
            cap = _nested_get(routing, ("preflight", "max_p95_latency_ms"))
            if isinstance(cap, (int, float)) and observed_p95 >= cap * latency_headroom_ratio:
                suggested = int(max(observed_p95 * 1.2, cap))
                suggestions.append(
                    {
                        "field": "preflight.max_p95_latency_ms",
                        "current": cap,
                        "suggested": suggested,
                        "reason": (
                            f"Observed fleet max p95 latency {int(observed_p95)}ms is "
                            f"within {int(latency_headroom_ratio * 100)}% of cap {int(cap)}ms."
                        ),
                        "confidence": "medium",
                    },
                )

    selection = aggregate.get("model_selection")
    if isinstance(selection, dict):
        primary_n = int(selection.get("primary_count") or 0)
        fallback_n = int(selection.get("fallback_count") or 0)
        total = primary_n + fallback_n
        if total > 0 and fallback_n / total >= fallback_rate_threshold:
            primary_id = _nested_get(routing, ("models", "primary", "id"))
            fallbacks = _nested_get(routing, ("models", "fallbacks"))
            first_fallback = None
            if isinstance(fallbacks, list) and fallbacks:
                fb0 = fallbacks[0]
                if isinstance(fb0, dict):
                    first_fallback = fb0.get("id")
            suggestions.append(
                {
                    "field": "models.primary.id",
                    "current": primary_id,
                    "suggested": first_fallback or primary_id,
                    "reason": (
                        f"Fallback model selected in {fallback_n}/{total} runs "
                        f"(>={int(fallback_rate_threshold * 100)}%). "
                        "Review primary availability or promote a stable fallback."
                    ),
                    "confidence": "low" if first_fallback is None else "medium",
                    "read_only_note": "Apply manually; this CLI never writes routing YAML.",
                },
            )

    timeout = _nested_get(routing, ("runtime", "request_timeout_seconds"))
    roles = aggregate.get("roles")
    if isinstance(roles, dict) and isinstance(timeout, (int, float)):
        max_stage_p95 = 0
        for role_doc in roles.values():
            if not isinstance(role_doc, dict):
                continue
            dur = role_doc.get("stage_duration_ms")
            if isinstance(dur, dict):
                p95 = dur.get("p95")
                if isinstance(p95, int):
                    max_stage_p95 = max(max_stage_p95, p95)
        if max_stage_p95 > int(timeout * 1000 * latency_headroom_ratio):
            suggested_timeout = int(max(timeout * 1.25, max_stage_p95 / 1000 + 30))
            suggestions.append(
                {
                    "field": "runtime.request_timeout_seconds",
                    "current": timeout,
                    "suggested": suggested_timeout,
                    "reason": (
                        f"Observed stage p95 {max_stage_p95}ms approaches "
                        f"request_timeout_seconds={timeout}."
                    ),
                    "confidence": "medium",
                },
            )

    max_output = _nested_get(routing, ("models", "primary", "max_output_tokens"))
    if isinstance(max_output, int) and isinstance(roles, dict):
        peak_completion = 0
        for role_doc in roles.values():
            if not isinstance(role_doc, dict):
                continue
            hints = role_doc.get("token_hints")
            if isinstance(hints, dict):
                ct = hints.get("completion_tokens_total")
                if isinstance(ct, int):
                    peak_completion = max(peak_completion, ct)
        if peak_completion > 0 and peak_completion >= max_output * latency_headroom_ratio:
            suggestions.append(
                {
                    "field": "models.primary.max_output_tokens",
                    "current": max_output,
                    "suggested": max(max_output, int(peak_completion * 1.25)),
                    "reason": (
                        f"Observed completion token hints peak at {peak_completion} "
                        f"near max_output_tokens={max_output}."
                    ),
                    "confidence": "low",
                },
            )

    return suggestions


def enrich_aggregate_with_model_selection(
    aggregate: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Count primary vs fallback model selection events."""
    primary = 0
    fallback = 0
    for row in rows:
        et = str(row.get("event_type", ""))
        if et == "model.selected.primary":
            primary += 1
        elif et == "model.selected.fallback":
            fallback += 1
    if primary or fallback:
        out = dict(aggregate)
        out["model_selection"] = {
            "primary_count": primary,
            "fallback_count": fallback,
        }
        return out
    return aggregate
