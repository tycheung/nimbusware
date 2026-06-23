from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, ValidationInfo, model_validator

from agent_core.models.events_foundation import RoleId, Severity, Verdict
from agent_core.models.events_payloads_base import (
    BasePayload,
    RequiredFixArtifact,
    _strictness_from_validation_info,
    finding_severity_requires_fixes,
)


class StageStartedPayload(BasePayload):
    stage_name: str
    attempt: int = Field(ge=1)


class StageBlockedPayload(BasePayload):
    stage_name: str
    blocker_count: int = Field(ge=1)
    owner_role: RoleId


class StagePassedPayload(BasePayload):
    stage_name: str
    duration_ms: int = Field(ge=0)


class StageFailedPayload(BasePayload):
    stage_name: str
    reason_code: str
    message: str


class CriticVerdictEmittedPayload(BasePayload):
    critic_role: RoleId
    verdict: Verdict
    severity: Severity
    owner_role: RoleId
    is_in_domain: bool
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Artifact paths, test names, or stable ids cited by the critic",
    )
    finding_ids: list[UUID] = Field(default_factory=list)
    required_fixes: list[RequiredFixArtifact] = Field(default_factory=list)

    @model_validator(mode="after")
    def verdict_and_severity_consistency(self) -> CriticVerdictEmittedPayload:
        fixes = self.required_fixes
        match self.verdict:
            case Verdict.PASS:
                if self.severity == Severity.BLOCKER:
                    raise ValueError("PASS verdict cannot use BLOCKER severity")
                if fixes:
                    raise ValueError("PASS verdict must not include required_fixes")
            case Verdict.NEEDS_INFO:
                if self.severity == Severity.BLOCKER:
                    raise ValueError("NEEDS_INFO verdict cannot use BLOCKER severity")
                if self.severity not in (Severity.LOW, Severity.MEDIUM):
                    raise ValueError(
                        "NEEDS_INFO verdict allows only LOW or MEDIUM severity",
                    )
            case Verdict.FAIL:
                if not fixes:
                    raise ValueError(
                        "FAIL verdict requires at least one RequiredFixArtifact",
                    )
        return self


class FindingCreatedPayload(BasePayload):
    finding_id: UUID
    category: str
    owner_role: RoleId
    severity: Severity
    source_artifact: str
    repro_steps: list[str] = Field(default_factory=list)
    required_fixes: list[RequiredFixArtifact] = Field(default_factory=list)

    @model_validator(mode="after")
    def severity_requires_fixes_per_policy(
        self,
        info: ValidationInfo,
    ) -> FindingCreatedPayload:
        settings = _strictness_from_validation_info(info)
        if finding_severity_requires_fixes(self.severity, settings) and not self.required_fixes:
            raise ValueError(
                "Finding severity and finding_fix_strictness policy require at least one "
                "RequiredFixArtifact (see FindingFixStrictnessSettings: "
                "minimum_severity_requiring_fixes, also_require_fixes_for_low_severity)",
            )
        return self


class FindingRoutedPayload(BasePayload):
    finding_id: UUID
    from_role: RoleId
    to_role: RoleId
    reason: str


class FindingClosedPayload(BasePayload):
    finding_id: UUID
    closed_by_role: RoleId
    resolution: str


class GateDecisionEmittedPayload(BasePayload):
    stage_name: str
    verdict: Verdict
    unanimous_pass_required: bool = True
    failing_critics: list[RoleId] = Field(
        default_factory=list,
        description="Role Registry ids for critics that failed the gate.",
    )
    failing_finding_ids: list[UUID] = Field(default_factory=list)
    failure_reason_code: str | None = Field(
        default=None,
        description=("For FAIL when no critic/finding ids apply yet (e.g. timeout, runner crash)."),
    )

    @model_validator(mode="after")
    def fail_implies_signals(self) -> GateDecisionEmittedPayload:
        if self.verdict != Verdict.FAIL:
            if self.failure_reason_code is not None:
                raise ValueError(
                    "failure_reason_code is only allowed when verdict is FAIL",
                )
            return self
        has_critics = bool(self.failing_critics)
        has_findings = bool(self.failing_finding_ids)
        code = (self.failure_reason_code or "").strip()
        if has_critics or has_findings or code:
            return self
        raise ValueError(
            "FAIL gate decision requires failing_critics, failing_finding_ids, "
            "or a non-empty failure_reason_code",
        )


class GateOverriddenPayload(BasePayload):
    actor_id: str = Field(min_length=1)
    reason_code: str = Field(min_length=1)
    stage_name: str = Field(min_length=1)
    policy_snapshot_id: str | None = None


class SelfRefinementLoopSignalledPayload(BasePayload):
    phase: Literal["D"] = "D"
    stage_name: str = "self_refinement:policy"
    attempt: int = Field(ge=1)
    max_iterations: int = Field(ge=1)
    signal: Literal["phase_d_kickoff", "phase_d_iteration"] = "phase_d_kickoff"
    gate_decision: Literal["proceed", "hold"] = "hold"
    evaluation_status: Literal["ok", "invalid", "gap"] | None = None
    loops_remaining: int = Field(default=0, ge=0)
    iteration_progress_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    should_continue: bool = False
    orchestration_branch: Literal["rules", "rules_with_llm_critique"] = "rules"
    llm_critique_enabled: bool = False
    llm_critique_attempted: bool = False
    llm_critique_verdict: Verdict | None = None
    llm_gate_decision: Literal["proceed", "hold"] | None = None


class MemoryRetrievalEmittedPayload(BasePayload):
    stage_name: str = Field(min_length=1, max_length=256)
    slice_id: str | None = Field(default=None, max_length=128)
    query_digest: str = Field(min_length=8, max_length=64)
    hit_chunk_ids: list[str] = Field(default_factory=list, max_length=20)
    excerpt_chars: int = Field(ge=0)
    retrieval_k: int = Field(ge=0, le=20)
    repo_scope_hash: str = Field(min_length=8, max_length=64)
    generation_id: str | None = Field(default=None, max_length=64)
