from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty
from orchestrator.role_telemetry import aggregate_role_telemetry_rows

_DEFAULT_COST_PER_1K_TOKENS_USD = 0.003


def summarize_run_role_cost(
    rows: list[dict[str, Any]],
    *,
    routing: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    doc = aggregate_role_telemetry_rows(rows)
    roles = mapping_or_empty(doc.get("roles"))
    if not roles:
        return None
    prompt_total = 0
    completion_total = 0
    latency_samples: list[int] = []
    for role_doc in roles.values():
        hints = mapping_or_empty(role_doc.get("token_hints"))
        prompt_total += int(hints.get("prompt_tokens_total") or 0)
        completion_total += int(hints.get("completion_tokens_total") or 0)
        lat = mapping_or_empty(role_doc.get("inference_latency_ms"))
        p95 = lat.get("p95")
        if isinstance(p95, int):
            latency_samples.append(p95)
    if not prompt_total and not completion_total and not latency_samples:
        return None
    cloud = mapping_or_empty((routing or {}).get("cloud_runtime"))
    cloud_enabled = bool(cloud.get("enabled"))
    token_total = prompt_total + completion_total
    cost_usd = None
    if cloud_enabled and token_total:
        rate = float(cloud.get("cost_per_1k_tokens_usd") or _DEFAULT_COST_PER_1K_TOKENS_USD)
        cost_usd = round((token_total / 1000.0) * rate, 4)
    summary: dict[str, Any] = {
        "prompt_tokens": prompt_total,
        "completion_tokens": completion_total,
        "token_total": token_total,
        "cloud_enabled": cloud_enabled,
    }
    if latency_samples:
        summary["inference_p95_ms"] = max(latency_samples)
    if cost_usd is not None:
        summary["estimated_cost_usd"] = cost_usd
    preset = (routing or {}).get("routing_preset_id")
    if isinstance(preset, str) and preset.strip():
        summary["routing_preset_id"] = preset.strip()
    return summary
