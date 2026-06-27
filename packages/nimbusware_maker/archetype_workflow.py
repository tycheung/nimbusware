from __future__ import annotations

FULLSTACK_CAMPAIGN_PROFILES = frozenset(
    {
        "campaign_fullstack",
        "safe_coding_campaign_fullstack",
    },
)


def campaign_profile_for_archetype(
    *,
    setup_bundle: str = "default",
    archetype: str | None = None,
    scope_narrowed: bool = False,
    workflow_hint: str | None = None,
) -> str:
    if scope_narrowed:
        return "campaign_micro_slice"
    arch = (archetype or "").strip().lower().replace("-", "_")
    hint = (workflow_hint or "").strip().lower()
    if arch in {"safe_coding", "a1"} or hint == "safe_coding":
        return "safe_coding_campaign_fullstack"
    return "campaign_fullstack"


def resolve_start_workflow_profile(
    profile: str,
    *,
    work_type: str,
) -> str:
    key = (profile or "").strip()
    wt = (work_type or "").strip().lower()
    if wt in {"campaign", "factory"}:
        if key == "safe_coding":
            return "safe_coding_campaign_fullstack"
        if key == "micro_slice" and wt == "campaign":
            return ""
    return key
