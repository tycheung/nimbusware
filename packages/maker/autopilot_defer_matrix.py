from __future__ import annotations

from typing import Any

_FORBIDDEN_AUTO_DEFER_FIELDS = frozenset({"hosting", "data_residency"})


def autopilot_may_auto_defer(
    *,
    setup_bundle: str = "default",
    archetype: str | None = None,
    trust_score: float | None = None,
    tenant_policy: dict[str, Any] | None = None,
    field_id: str | None = None,
) -> bool:
    bundle = (setup_bundle or "default").strip().lower()
    arch = (archetype or "").strip().lower().replace("-", "_")
    policy = tenant_policy if isinstance(tenant_policy, dict) else {}

    if field_id and field_id in _FORBIDDEN_AUTO_DEFER_FIELDS:
        forbidden = policy.get("forbid_auto_defer_fields")
        if isinstance(forbidden, list) and field_id in forbidden:
            return False
        if bundle == "enterprise":
            return False

    if arch in {"safe_coding", "a1"}:
        return False

    if bundle == "enterprise":
        return bool(policy.get("allow_autopilot_auto_defer", False))

    if arch in {"engineer_workspace", "engineer", "a2"}:
        score = trust_score if trust_score is not None else 7.0
        return score >= 7.0

    return True
