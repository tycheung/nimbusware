from uuid import uuid4

from nimbusware_orchestrator.mesh_optimizer import (
    normalize_optimizer_weights,
    pick_optimize_node,
    score_node,
    weights_from_priority,
)


def test_weights_from_priority_orders_descending() -> None:
    weights = weights_from_priority(["latency", "headroom", "cost", "model_fit"])
    assert weights["latency"] > weights["headroom"] > weights["cost"]


def test_score_node_prefers_headroom() -> None:
    low = {"claims_total": 4, "claims_used": 3}
    high = {"claims_total": 8, "claims_used": 1}
    w = normalize_optimizer_weights({"headroom": 1.0, "model_fit": 0, "latency": 0, "cost": 0})
    assert score_node(high, w) > score_node(low, w)


def test_pick_optimize_node_uses_weights() -> None:
    n1, n2 = uuid4(), uuid4()
    caps = {
        n1: {"claims_total": 4, "claims_used": 3},
        n2: {"claims_total": 8, "claims_used": 1},
    }
    w = normalize_optimizer_weights({"headroom": 1.0, "model_fit": 0, "latency": 0, "cost": 0})
    picked = pick_optimize_node([n1, n2], node_capabilities=caps, weights=w)
    assert picked == n2
