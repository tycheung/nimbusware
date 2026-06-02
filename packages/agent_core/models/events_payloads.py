from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from agent_core.models.events_foundation import RoleId, Severity, Verdict


class BasePayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        protected_namespaces=(),
        populate_by_name=True,
    )


FINDING_FIX_STRICTNESS_CONTEXT_KEY = "finding_fix_strictness"

_SEVERITY_ORDER: tuple[Severity, ...] = (
    Severity.LOW,
    Severity.MEDIUM,
    Severity.HIGH,
    Severity.BLOCKER,
)


def _severity_rank(severity: Severity) -> int:
    return _SEVERITY_ORDER.index(severity)


class FindingFixStrictnessSettings(BasePayload):
    """Two-axis policy for when `FindingCreatedPayload` must include `required_fixes`.

    Primary (floor): all severities **at or above** `minimum_severity_requiring_fixes` in the
    ladder LOW < MEDIUM < HIGH < BLOCKER require fixes.

    Secondary: when `also_require_fixes_for_low_severity` is True, **LOW** findings also require
    fixes even if the primary floor is above LOW (e.g. floor MEDIUM still mandates fixes for LOW).
    """

    minimum_severity_requiring_fixes: Severity = Severity.MEDIUM
    also_require_fixes_for_low_severity: bool = False


DEFAULT_FINDING_FIX_STRICTNESS = FindingFixStrictnessSettings()


class NetworkEgressPolicySnapshot(BasePayload):
    """Frozen ``policy_snapshot.network_egress`` (plan ?6.3A).

    Layer merge is orchestration's job; this model validates the merged shape only.
    """

    scraper_role_allowlist: list[RoleId] = Field(default_factory=list)
    domain_allowlist: list[str] = Field(default_factory=list)
    budget_bytes_per_run: int | None = None

    @field_validator("budget_bytes_per_run")
    @classmethod
    def budget_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError(
                "budget_bytes_per_run must be null or a non-negative integer (plan ?6.3A)",
            )
        return v


class PolicySnapshotV1(BasePayload):
    """Immutable policy snapshot at run start (plan ?6.3A)."""

    finding_fix_strictness: FindingFixStrictnessSettings
    network_egress: NetworkEgressPolicySnapshot


def finding_severity_requires_fixes(
    severity: Severity,
    settings: FindingFixStrictnessSettings,
) -> bool:
    """Return True if policy requires at least one RequiredFixArtifact for this severity."""
    if _severity_rank(severity) >= _severity_rank(settings.minimum_severity_requiring_fixes):
        return True
    if settings.also_require_fixes_for_low_severity and severity == Severity.LOW:
        return True
    return False


def _strictness_from_validation_info(info: ValidationInfo) -> FindingFixStrictnessSettings:
    ctx = info.context or {}
    raw = ctx.get(FINDING_FIX_STRICTNESS_CONTEXT_KEY)
    if raw is None:
        return DEFAULT_FINDING_FIX_STRICTNESS
    if isinstance(raw, FindingFixStrictnessSettings):
        return raw
    if isinstance(raw, dict):
        return FindingFixStrictnessSettings.model_validate(raw)
    raise TypeError(
        f"{FINDING_FIX_STRICTNESS_CONTEXT_KEY!r} must be "
        "FindingFixStrictnessSettings or a dict, or omitted for defaults",
    )


class RequiredFixArtifact(BasePayload):
    """Machine-actionable remediation; mirrors plan ?4.2 / ?19.1."""

    artifact_schema_version: Literal[1] = 1
    patch_format: Literal["json_patch", "unified_diff"] = Field(
        alias="format",
        description="Wire / JSON key remains `format` (plan + configs).",
    )
    target_files: list[str] = Field(min_length=1)
    patch_artifact: str = Field(min_length=1)
    validation_steps: list[str] = Field(
        min_length=1,
        description="Named checks or command ids to rerun after apply",
    )
    acceptance_criteria: str = Field(
        min_length=1,
        description="Objective signal that closes the finding (e.g. test name, exit code)",
    )


class RunCreatedPayload(BasePayload):
    workflow_profile: str
    policy_version: str
    config_snapshot_id: str
    policy_snapshot: PolicySnapshotV1 | None = Field(
        default=None,
        description=(
            "Frozen policy at run start (plan ?6.3A); omit until orchestration supplies it."
        ),
    )


class RunStartedPayload(BasePayload):
    started_by: str


class RunFailedPayload(BasePayload):
    reason_code: str
    message: str


class RunCompletedPayload(BasePayload):
    summary: str


class RunEscalatedPayload(BasePayload):
    """Human escalation / arbiter checkpoint (plan ?6.6)."""

    actor_id: str = Field(min_length=1, description="Human or system actor identifier.")
    reason_code: str = Field(min_length=1)
    policy_snapshot_id: str | None = None
    notes: str | None = None


class GateOverriddenPayload(BasePayload):
    """Recorded human override of a gate outcome (plan ?6.6)."""

    actor_id: str = Field(min_length=1)
    reason_code: str = Field(min_length=1)
    stage_name: str = Field(min_length=1)
    policy_snapshot_id: str | None = None


class ModelPreflightStartedPayload(BasePayload):
    provider: str
    base_url: str
    requested_model_id: str


class ModelPreflightPassedPayload(BasePayload):
    provider: str
    validated_model_id: str
    context_tokens: int = Field(ge=1)
    p95_latency_ms: int = Field(ge=0)
    checks_passed: list[str] = Field(default_factory=list)
    preflight_latency_sample_count: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Health endpoint multisample count when measured (plan ?4.4).",
    )
    p95_latency_source: str | None = Field(
        default=None,
        max_length=256,
        description="Short hint for how p95_latency_ms was derived (e.g. health vs json probe).",
    )
    health_latency_samples_ms: list[int] | None = Field(
        default=None,
        max_length=20,
        description=(
            "Per-sample health probe latencies in ms when multisample "
            "(plan ?4.4). Defaults to None when omitted from stored payloads / "
            "single-sample runs; aligned with `preflight_latency_sample_count`."
        ),
    )

    @field_validator("health_latency_samples_ms")
    @classmethod
    def _validate_samples_non_negative(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return None
        for s in v:
            if not isinstance(s, int) or isinstance(s, bool):
                msg = "health_latency_samples_ms entries must be int"
                raise ValueError(msg)
            if s < 0:
                msg = "health_latency_samples_ms entries must be >= 0"
                raise ValueError(msg)
        return v


class ModelPreflightFailedPayload(BasePayload):
    provider: str
    requested_model_id: str
    reason_code: str
    failed_checks: list[str] = Field(default_factory=list)
    fallback_attempted: bool = False


class ModelSelectedPrimaryPayload(BasePayload):
    provider: str
    model_id: str


class ModelSelectedFallbackPayload(BasePayload):
    provider: str
    selected_model_id: str
    reason_code: str
    original_model_id: str


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
        description="Role Registry ids for critics that failed the gate (plan ?3).",
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


class PersonaShelfUpdatedPayload(BasePayload):
    """Audit record for a write through ``POST/PUT/PATCH/DELETE /v1/personas/...``.

    Distinct from per-run events: ``run_id`` on the envelope is the API caller's
    correlation, NOT a real run (the persona catalog is repo-scoped). Persists
    in the same event store so operators can reconstruct edit history from one
    source.
    """

    shelf: Literal["business_area", "development_role"]
    persona_id: str = Field(min_length=1, max_length=200)
    prev_version: int = Field(ge=0, description="0 on first create; >=1 thereafter.")
    next_version: int = Field(ge=1)
    fields_changed: list[str] = Field(
        default_factory=list,
        max_length=16,
        description=(
            "Field names mutated by the request (subset of the PersonaEntry schema). "
            "Use the sentinel value '__deleted__' to mark a DELETE."
        ),
    )
    actor: str | None = Field(default=None, max_length=200)

    @field_validator("fields_changed")
    @classmethod
    def _fields_changed_non_empty_strings(cls, v: list[str]) -> list[str]:
        for i, name in enumerate(v):
            if not isinstance(name, str) or not name:
                raise ValueError(
                    f"fields_changed[{i}] must be a non-empty string (got {name!r})",
                )
        return v

    @model_validator(mode="after")
    def _validate_version_monotonic(self) -> PersonaShelfUpdatedPayload:
        if self.next_version <= self.prev_version:
            raise ValueError(
                "persona.shelf.updated: next_version must be strictly greater than prev_version",
            )
        return self


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


class MemoryIndexedPayload(BasePayload):
    """Audit record after a repo-scoped memory index rebuild."""

    repo_scope_hash: str = Field(min_length=8, max_length=64)
    generation_id: str = Field(min_length=8, max_length=64)
    chunks_added: int = Field(ge=0)
    chunks_skipped: int = Field(ge=0)
    embedding_mode: Literal["deterministic", "ollama"] = "deterministic"
    embedding_model_id: str = Field(min_length=1, max_length=128)
    index_dir: str | None = Field(default=None, max_length=512)


class MemoryRetrievalEmittedPayload(BasePayload):
    """Audit record when memory hits are injected into a stage."""

    stage_name: str = Field(min_length=1, max_length=256)
    query_digest: str = Field(min_length=8, max_length=64)
    hit_chunk_ids: list[str] = Field(default_factory=list, max_length=20)
    excerpt_chars: int = Field(ge=0)
    retrieval_k: int = Field(ge=0, le=20)
    repo_scope_hash: str = Field(min_length=8, max_length=64)
    generation_id: str | None = Field(default=None, max_length=64)


class ResearchBriefSourcePayload(BasePayload):
    url: str = Field(min_length=1, max_length=2048)
    license: str = Field(min_length=1, max_length=64)
    trust_tier: Literal["high", "medium", "low"] = "medium"


class ResearchBriefEmittedPayload(BasePayload):
    brief_kind: Literal["domain", "code"]
    domain_tag: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=8000)
    artifact_id: str = Field(min_length=1, max_length=128)
    sources: list[ResearchBriefSourcePayload] = Field(default_factory=list, max_length=20)


class ResearchPatternIndexedPayload(BasePayload):
    pattern_id: str = Field(min_length=1, max_length=128)
    repo_url: str = Field(min_length=1, max_length=2048)
    paths: list[str] = Field(default_factory=list, max_length=40)
    license: str = Field(min_length=1, max_length=64)
    embedding_ref: str = Field(min_length=1, max_length=128)


class DomainCriticProposedPayload(BasePayload):
    critic_template: str = Field(min_length=1, max_length=256)
    allowed_domains: list[str] = Field(default_factory=list, max_length=16)
    blocking_authority: Literal["ADVISORY", "BLOCKING"] = "ADVISORY"
    evidence_refs: list[str] = Field(default_factory=list, max_length=16)


class StitchLicenseCheckedPayload(BasePayload):
    detected_licenses: list[str] = Field(default_factory=list, max_length=16)
    allowlist: list[str] = Field(default_factory=list, max_length=16)
    passed: bool
    evidence_refs: list[str] = Field(default_factory=list, max_length=16)


class StitchDependencyCheckedPayload(BasePayload):
    declared_deps: list[str] = Field(default_factory=list, max_length=40)
    new_deps: list[str] = Field(default_factory=list, max_length=20)
    max_allowed: int = Field(ge=0, le=50)
    passed: bool
    reason_code: str | None = Field(default=None, max_length=64)


class StitchPlanEmittedPayload(BasePayload):
    target_paths: list[str] = Field(default_factory=list, max_length=40)
    source_manifest_id: str = Field(min_length=1, max_length=128)
    wiring_delta_summary: str = Field(min_length=1, max_length=4000)


class StitchAppliedPayload(BasePayload):
    snapshot_ref: str = Field(min_length=1, max_length=256)
    files_added: list[str] = Field(default_factory=list, max_length=40)
    deps_added: list[str] = Field(default_factory=list, max_length=20)


class StitchFailedPayload(BasePayload):
    reason_code: str = Field(min_length=1, max_length=64)
    rollback_snapshot_ref: str | None = Field(default=None, max_length=256)
