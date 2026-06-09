from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from nimbusware_orchestrator.autopilot_profiles import deliberation_rounds_for_level


class HardBlockCategory(str, Enum):
    SECURITY_P0 = "security_p0"
    POLICY_VIOLATION = "policy_violation"
    GOVERNOR_CAP = "governor_cap"
    NEEDS_OPERATOR = "needs_operator"


HARD_BLOCK_KINDS = frozenset(
    {
        "injection",
        "auth_bypass",
        "policy_violation",
        "egress_violation",
        "governor_cap",
        "needs_operator",
    },
)


@dataclass
class ResolutionVerdict:
    accord: bool
    hard_block: bool
    rounds: int
    detail: str
    dissent: list[str] = field(default_factory=list)


@dataclass
class ResolutionCouncilResult:
    verdict: ResolutionVerdict
    stage: str = "resolution.council"

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "accord": self.verdict.accord,
            "hard_block": self.verdict.hard_block,
            "rounds": self.verdict.rounds,
            "detail": self.verdict.detail,
            "dissent": self.verdict.dissent,
        }


def classify_hard_block(finding_kind: str, *, severity: str = "") -> bool:
    kind = finding_kind.lower()
    if kind in HARD_BLOCK_KINDS:
        return True
    if severity.lower() == "security_p0":
        return True
    return False


def run_resolution_council(
    *,
    findings: list[dict[str, Any]],
    autopilot_level: int = 5,
    max_rounds: int | None = None,
) -> ResolutionCouncilResult:
    rounds = (
        max_rounds if max_rounds is not None else deliberation_rounds_for_level(autopilot_level)
    )
    hard = [
        f
        for f in findings
        if classify_hard_block(str(f.get("kind", "")), severity=str(f.get("severity", "")))
    ]
    if hard:
        return ResolutionCouncilResult(
            verdict=ResolutionVerdict(
                accord=False,
                hard_block=True,
                rounds=0,
                detail="hard_block_allowlist",
            ),
        )
    if rounds == 0:
        return ResolutionCouncilResult(
            verdict=ResolutionVerdict(
                accord=False,
                hard_block=False,
                rounds=0,
                detail="operator_pause",
            ),
        )
    remediable = [f for f in findings if not classify_hard_block(str(f.get("kind", "")))]
    accord = len(remediable) == 0 or autopilot_level >= 6
    detail = "accord_fix_slice" if accord else "pause_for_operator"
    return ResolutionCouncilResult(
        verdict=ResolutionVerdict(
            accord=accord,
            hard_block=False,
            rounds=rounds,
            detail=detail,
            dissent=[str(f.get("message", ""))[:200] for f in remediable[:5]],
        ),
    )
