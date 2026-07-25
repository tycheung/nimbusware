from __future__ import annotations

from enum import Enum

from orchestrator.improvement.improvement_council import CouncilVote, ImprovementTrack


class RepoScope(str, Enum):
    GREENFIELD = "greenfield"
    MAINTAIN = "maintain"
    HARDEN = "harden"


_SCOPE_MATRIX: dict[RepoScope, frozenset[ImprovementTrack]] = {
    RepoScope.GREENFIELD: frozenset(
        {
            ImprovementTrack.IMPLEMENT_PLANNED,
            ImprovementTrack.DISCOVER_FEATURES,
            ImprovementTrack.DOCUMENT_CONTRACTS,
            ImprovementTrack.ARCHITECTURE_REVISE,
            ImprovementTrack.VARIANT_EXPERIMENT,
            ImprovementTrack.DISTILL_ARTIFACTS,
            ImprovementTrack.RESEARCH_HARNESS,
            ImprovementTrack.TRY_DIVERSE_REPO,
            ImprovementTrack.RESEARCH_DOMAIN,
        },
    ),
    RepoScope.MAINTAIN: frozenset(
        {
            ImprovementTrack.SIMPLIFY,
            ImprovementTrack.REFACTOR_COHESION,
            ImprovementTrack.IMPROVE_COVERAGE,
            ImprovementTrack.IMPLEMENT_PLANNED,
            ImprovementTrack.RESEARCH_TRANSPLANT,
            ImprovementTrack.SECURITY_HARDEN,
            ImprovementTrack.PERFORMANCE_TUNE,
            ImprovementTrack.ARCHITECTURE_REVISE,
            ImprovementTrack.DOCUMENT_CONTRACTS,
            ImprovementTrack.DISTILL_ARTIFACTS,
            ImprovementTrack.RESEARCH_HARNESS,
            ImprovementTrack.TRY_DIVERSE_REPO,
            ImprovementTrack.RESEARCH_DOMAIN,
        },
    ),
    RepoScope.HARDEN: frozenset(
        {
            ImprovementTrack.IMPROVE_COVERAGE,
            ImprovementTrack.SIMPLIFY,
            ImprovementTrack.SECURITY_HARDEN,
            ImprovementTrack.RESEARCH_TRANSPLANT,
            ImprovementTrack.DISTILL_ARTIFACTS,
            ImprovementTrack.RESEARCH_HARNESS,
            ImprovementTrack.RESEARCH_DOMAIN,
        },
    ),
}


def infer_repo_scope(*, loc: int, orphan_count: int, duplicate_clusters: int) -> RepoScope:
    if loc < 500 and orphan_count == 0:
        return RepoScope.GREENFIELD
    if duplicate_clusters > 2 or orphan_count > 5:
        return RepoScope.HARDEN
    return RepoScope.MAINTAIN


def filter_votes_by_scope(votes: list[CouncilVote], scope: RepoScope) -> list[CouncilVote]:
    allowed = _SCOPE_MATRIX.get(scope, _SCOPE_MATRIX[RepoScope.MAINTAIN])
    filtered = [v for v in votes if v.track in allowed]
    return filtered if filtered else votes[:1]
