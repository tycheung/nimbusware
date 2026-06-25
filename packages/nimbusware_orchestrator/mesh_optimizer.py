from __future__ import annotations

from uuid import UUID

from nimbusware_maker.optimizer_weights_store import DEFAULT_OPTIMIZER_WEIGHTS


def normalize_optimizer_weights(raw: dict[str, float] | None) -> dict[str, float]:
    if not raw:
        return dict(DEFAULT_OPTIMIZER_WEIGHTS)
    out: dict[str, float] = {}
    for key, default in DEFAULT_OPTIMIZER_WEIGHTS.items():
        try:
            out[key] = float(raw.get(key, default))
        except (TypeError, ValueError):
            out[key] = default
    return out


def weights_from_priority(priority: list[str]) -> dict[str, float]:
    keys = [k for k in priority if k in DEFAULT_OPTIMIZER_WEIGHTS]
    if not keys:
        keys = list(DEFAULT_OPTIMIZER_WEIGHTS.keys())
    total = sum(range(1, len(keys) + 1))
    return {key: (len(keys) - idx) / total for idx, key in enumerate(keys)}


def score_node(caps: dict[str, object], weights: dict[str, float]) -> float:
    def _cap_float(*keys: str, default: float = 0.5) -> float:
        for key in keys:
            val = caps.get(key)
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                try:
                    return float(val)
                except ValueError:
                    continue
        return default

    total = _cap_float("claims_total", "max_parallel_claims", default=4.0)
    used = _cap_float("claims_used", "active_claims", default=0.0)
    headroom = max(0.0, (total - used) / total) if total > 0 else 0.5
    fit = _cap_float("model_fit_score", default=0.5)
    latency_ms = _cap_float("latency_p95_ms", default=0.0)
    latency = 1.0 - min(1.0, latency_ms / 5000.0)
    cost = _cap_float("cost_score", default=0.5)
    w = normalize_optimizer_weights(weights)
    return (
        w["headroom"] * headroom + w["model_fit"] * fit + w["latency"] * latency + w["cost"] * cost
    )


def pick_optimize_node(
    nodes: list[UUID],
    *,
    node_capabilities: dict[UUID, dict[str, object]] | None,
    weights: dict[str, float] | None,
    used_nodes: set[UUID] | None = None,
) -> UUID | None:
    if not nodes:
        return None
    caps_map = node_capabilities or {}
    used = used_nodes or set()
    candidates = [n for n in nodes if n not in used] or list(nodes)
    return max(candidates, key=lambda n: score_node(caps_map.get(n, {}), weights or {}))
