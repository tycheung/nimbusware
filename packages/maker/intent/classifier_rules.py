from __future__ import annotations

from enum import Enum

PATCH_KEYWORDS = (
    "fix",
    "bug",
    "broken",
    "error",
    "failing",
    "fail",
    "crash",
    "regression",
    "typo",
    "hotfix",
    "stack trace",
    "traceback",
    "assertionerror",
    "exception",
)
CAMPAIGN_KEYWORDS = (
    "build app",
    "build a",
    "mvp",
    "crm",
    "deliver",
    "autonomous",
    "full application",
    "from scratch",
    "product",
    "saas",
)
SLICE_KEYWORDS = (
    "add feature",
    "add a feature",
    "refactor",
    "implement",
    "extend",
    "module",
    "component",
    "endpoint",
    "api route",
)
FACTORY_KEYWORDS = ("factory", "zero-touch", "zero touch", "catalog prompt")
FAST_SLICE_KEYWORDS = ("fast slice", "quick slice")
SELF_EVOLVE_KEYWORDS = (
    "self evolve",
    "self-evolve",
    "self evolution",
    "self-evolution",
    "improve yourself",
    "get better at",
    "study other harness",
    "study agent harness",
    "other agentic",
    "agent frameworks",
    "diverse repos",
    "diverse projects",
    "curriculum evolve",
    "meta research",
    "learn from other agents",
    "domain knowledge",
    "domain-specific",
    "domain specific",
    "learn the domain",
)


class WorkType(str, Enum):
    QUICK = "quick"
    PATCH = "patch"
    SLICE = "slice"
    CAMPAIGN = "campaign"
    FACTORY = "factory"
    SELF_EVOLVE = "self_evolve"


PROFILE_BY_WORK_TYPE: dict[WorkType, str] = {
    WorkType.QUICK: "quick_local",
    WorkType.PATCH: "patch",
    WorkType.SLICE: "micro_slice",
    WorkType.CAMPAIGN: "campaign_fullstack",
    WorkType.FACTORY: "campaign_factory_zero_touch",
    WorkType.SELF_EVOLVE: "campaign_self_evolve",
}

BACKEND_ONLY_PHRASES = (
    "backend only",
    "api only",
    "rest api only",
    "no frontend",
    "no ui",
    "python only",
    "backend-only",
    "api-only",
)
