from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from orchestrator.profiles.autopilot_profiles import deliberation_rounds_for_level


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
    loc_accord: bool = True


@dataclass
class ResolutionSoakMetrics:
    autopilot_level: int = 0
    max_rounds: int = 0
    finding_count: int = 0
    remediable_count: int = 0
    hard_block: bool = False
    accord: bool = False
    debate_first: bool = False
    loc_accord: bool = True
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "autopilot_level": self.autopilot_level,
            "max_rounds": self.max_rounds,
            "finding_count": self.finding_count,
            "remediable_count": self.remediable_count,
            "hard_block": self.hard_block,
            "accord": self.accord,
            "debate_first": self.debate_first,
            "loc_accord": self.loc_accord,
            "detail": self.detail,
        }


@dataclass
class ResolutionCouncilResult:
    verdict: ResolutionVerdict
    stage: str = "resolution.council"
    soak: ResolutionSoakMetrics | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "stage": self.stage,
            "accord": self.verdict.accord,
            "hard_block": self.verdict.hard_block,
            "rounds": self.verdict.rounds,
            "detail": self.verdict.detail,
            "resolution_rationale": self.verdict.detail,
            "dissent": self.verdict.dissent,
            "loc_accord": self.verdict.loc_accord,
        }
        if self.soak is not None:
            payload["soak"] = self.soak.to_dict()
        return payload


def loc_accord_for_findings(findings: list[dict[str, Any]], *, loc_budget: int = 400) -> bool:
    total = 0
    for item in findings:
        loc_raw = item.get("loc_delta") or item.get("loc")
        if isinstance(loc_raw, (int, float)):
            total += int(loc_raw)
    return total <= loc_budget


def classify_hard_block(finding_kind: str, *, severity: str = "") -> bool:
    kind = finding_kind.lower()
    if kind in HARD_BLOCK_KINDS:
        return True
    if severity.lower() == "security_p0":
        return True
    return False


def build_resolution_soak_metrics(
    *,
    findings: list[dict[str, Any]],
    autopilot_level: int,
    verdict: ResolutionVerdict,
    max_rounds: int,
) -> ResolutionSoakMetrics:
    remediable = [
        f
        for f in findings
        if not classify_hard_block(str(f.get("kind", "")), severity=str(f.get("severity", "")))
    ]
    debate_first = (
        not verdict.hard_block
        and not verdict.accord
        and verdict.rounds > 0
        and verdict.detail in {"pause_for_operator", "loc_budget_exceeded"}
    )
    return ResolutionSoakMetrics(
        autopilot_level=autopilot_level,
        max_rounds=max_rounds,
        finding_count=len(findings),
        remediable_count=len(remediable),
        hard_block=verdict.hard_block,
        accord=verdict.accord,
        debate_first=debate_first,
        loc_accord=verdict.loc_accord,
        detail=verdict.detail,
    )


def aggregate_resolution_soak_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    for row in rows:
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        block = meta.get("resolution_council")
        if not isinstance(block, dict):
            continue
        soak = block.get("soak")
        if isinstance(soak, dict):
            samples.append(soak)
    total = len(samples)
    if total == 0:
        return {
            "resolution_council_runs": 0,
            "debate_first_rate": 0.0,
            "accord_rate": 0.0,
            "hard_block_rate": 0.0,
        }
    debate_first = sum(1 for s in samples if s.get("debate_first"))
    accord = sum(1 for s in samples if s.get("accord"))
    hard_block = sum(1 for s in samples if s.get("hard_block"))
    return {
        "resolution_council_runs": total,
        "debate_first_rate": round(debate_first / total, 4),
        "accord_rate": round(accord / total, 4),
        "hard_block_rate": round(hard_block / total, 4),
    }


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
        verdict = ResolutionVerdict(
            accord=False,
            hard_block=True,
            rounds=0,
            detail="hard_block_allowlist",
        )
        return ResolutionCouncilResult(
            verdict=verdict,
            soak=build_resolution_soak_metrics(
                findings=findings,
                autopilot_level=autopilot_level,
                verdict=verdict,
                max_rounds=rounds,
            ),
        )
    if rounds == 0:
        verdict = ResolutionVerdict(
            accord=False,
            hard_block=False,
            rounds=0,
            detail="operator_pause",
        )
        return ResolutionCouncilResult(
            verdict=verdict,
            soak=build_resolution_soak_metrics(
                findings=findings,
                autopilot_level=autopilot_level,
                verdict=verdict,
                max_rounds=rounds,
            ),
        )
    remediable = [f for f in findings if not classify_hard_block(str(f.get("kind", "")))]
    loc_ok = loc_accord_for_findings(remediable)
    accord = (len(remediable) == 0 or autopilot_level >= 6) and loc_ok
    detail = (
        "accord_fix_slice"
        if accord
        else ("loc_budget_exceeded" if not loc_ok else "pause_for_operator")
    )
    verdict = ResolutionVerdict(
        accord=accord,
        hard_block=False,
        rounds=rounds,
        detail=detail,
        dissent=[str(f.get("message", ""))[:200] for f in remediable[:5]],
        loc_accord=loc_ok,
    )
    return ResolutionCouncilResult(
        verdict=verdict,
        soak=build_resolution_soak_metrics(
            findings=findings,
            autopilot_level=autopilot_level,
            verdict=verdict,
            max_rounds=rounds,
        ),
    )
