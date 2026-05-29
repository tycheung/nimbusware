from __future__ import annotations

import math
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal, TypeAlias
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationInfo,
    field_validator,
    model_validator,
)

# Logical JSON contract for metadata (documentation + typing). Floats must be finite
# (RFC 8259-safe); runtime checks enforce this alongside the dict structure.
JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


def _is_json_value(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return True
    if isinstance(value, str):
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(k, str) and _is_json_value(v) for k, v in value.items()
        )
    return False


def _validate_envelope_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("metadata must be a dict")
    if not _is_json_value(value):
        raise ValueError(
            "metadata must be strict JSON-compatible (str keys; only None, bool, str, "
            "int, finite float, list, dict; no datetime/bytes/Decimal/set/NaN/inf)",
        )
    return value


EventMetadata = Annotated[dict[str, Any], AfterValidator(_validate_envelope_metadata)]


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKER = "BLOCKER"


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_INFO = "NEEDS_INFO"


class EventType(str, Enum):
    RUN_CREATED = "run.created"
    RUN_STARTED = "run.started"
    RUN_FAILED = "run.failed"
    RUN_COMPLETED = "run.completed"
    MODEL_PREFLIGHT_STARTED = "model.preflight.started"
    MODEL_PREFLIGHT_PASSED = "model.preflight.passed"
    MODEL_PREFLIGHT_FAILED = "model.preflight.failed"
    MODEL_SELECTED_PRIMARY = "model.selected.primary"
    MODEL_SELECTED_FALLBACK = "model.selected.fallback"
    STAGE_STARTED = "stage.started"
    STAGE_BLOCKED = "stage.blocked"
    STAGE_PASSED = "stage.passed"
    STAGE_FAILED = "stage.failed"
    CRITIC_VERDICT_EMITTED = "critic.verdict.emitted"
    FINDING_CREATED = "finding.created"
    FINDING_ROUTED = "finding.routed"
    FINDING_CLOSED = "finding.closed"
    GATE_DECISION_EMITTED = "gate.decision.emitted"
    RUN_ESCALATED = "run.escalated"
    GATE_OVERRIDDEN = "gate.overridden"
    PERSONA_SHELF_UPDATED = "persona.shelf.updated"
    SELF_REFINEMENT_LOOP_SIGNALLED = "self_refinement.loop.signalled"
    MEMORY_INDEXED = "memory.indexed"
    MEMORY_RETRIEVAL_EMITTED = "memory.retrieval.emitted"


RoleId: TypeAlias = UUID
"""Role Registry ``role_id`` on persisted paths (plan ?3, ?5, ?6.4). JSON wire: UUID string."""


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
        description=(
            "For FAIL when no critic/finding ids apply yet (e.g. timeout, runner crash)."
        ),
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


class BaseHermesEvent(BaseModel):
    """Shared envelope fields (DB assigns store_seq separately at persist time).

    ``actor_role`` is a Role Registry UUID when set (plan ?6.4, ?19.2).
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        protected_namespaces=(),
        populate_by_name=True,
    )

    event_id: UUID
    run_id: UUID
    occurred_at: datetime
    event_version: int = Field(default=1, ge=1)
    stage_id: UUID | None = None
    task_id: UUID | None = None
    actor_role: RoleId | None = None
    active_model_id: str | None = Field(
        default=None,
        alias="model_id",
        description="LLM id used for this event (JSON / DB column: model_id)",
    )
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    metadata: EventMetadata = Field(
        default_factory=dict,
        description="JSON-serializable audit context (see JsonValue contract).",
    )


class RunCreatedEvent(BaseHermesEvent):
    event_type: Literal[EventType.RUN_CREATED]
    payload: RunCreatedPayload


class RunStartedEvent(BaseHermesEvent):
    event_type: Literal[EventType.RUN_STARTED]
    payload: RunStartedPayload


class RunFailedEvent(BaseHermesEvent):
    event_type: Literal[EventType.RUN_FAILED]
    payload: RunFailedPayload


class RunCompletedEvent(BaseHermesEvent):
    event_type: Literal[EventType.RUN_COMPLETED]
    payload: RunCompletedPayload


class RunEscalatedEvent(BaseHermesEvent):
    event_type: Literal[EventType.RUN_ESCALATED]
    payload: RunEscalatedPayload


class GateOverriddenEvent(BaseHermesEvent):
    event_type: Literal[EventType.GATE_OVERRIDDEN]
    payload: GateOverriddenPayload


class ModelPreflightStartedEvent(BaseHermesEvent):
    event_type: Literal[EventType.MODEL_PREFLIGHT_STARTED]
    payload: ModelPreflightStartedPayload


class ModelPreflightPassedEvent(BaseHermesEvent):
    event_type: Literal[EventType.MODEL_PREFLIGHT_PASSED]
    payload: ModelPreflightPassedPayload


class ModelPreflightFailedEvent(BaseHermesEvent):
    event_type: Literal[EventType.MODEL_PREFLIGHT_FAILED]
    payload: ModelPreflightFailedPayload


class ModelSelectedPrimaryEvent(BaseHermesEvent):
    event_type: Literal[EventType.MODEL_SELECTED_PRIMARY]
    payload: ModelSelectedPrimaryPayload


class ModelSelectedFallbackEvent(BaseHermesEvent):
    event_type: Literal[EventType.MODEL_SELECTED_FALLBACK]
    payload: ModelSelectedFallbackPayload


class StageStartedEvent(BaseHermesEvent):
    event_type: Literal[EventType.STAGE_STARTED]
    payload: StageStartedPayload


class StageBlockedEvent(BaseHermesEvent):
    event_type: Literal[EventType.STAGE_BLOCKED]
    payload: StageBlockedPayload


class StagePassedEvent(BaseHermesEvent):
    event_type: Literal[EventType.STAGE_PASSED]
    payload: StagePassedPayload


class StageFailedEvent(BaseHermesEvent):
    event_type: Literal[EventType.STAGE_FAILED]
    payload: StageFailedPayload


class CriticVerdictEmittedEvent(BaseHermesEvent):
    event_type: Literal[EventType.CRITIC_VERDICT_EMITTED]
    payload: CriticVerdictEmittedPayload


class FindingCreatedEvent(BaseHermesEvent):
    event_type: Literal[EventType.FINDING_CREATED]
    payload: FindingCreatedPayload


class FindingRoutedEvent(BaseHermesEvent):
    event_type: Literal[EventType.FINDING_ROUTED]
    payload: FindingRoutedPayload


class FindingClosedEvent(BaseHermesEvent):
    event_type: Literal[EventType.FINDING_CLOSED]
    payload: FindingClosedPayload


class GateDecisionEmittedEvent(BaseHermesEvent):
    event_type: Literal[EventType.GATE_DECISION_EMITTED]
    payload: GateDecisionEmittedPayload


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


class PersonaShelfUpdatedEvent(BaseHermesEvent):
    event_type: Literal[EventType.PERSONA_SHELF_UPDATED]
    payload: PersonaShelfUpdatedPayload


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


class SelfRefinementLoopSignalledEvent(BaseHermesEvent):
    event_type: Literal[EventType.SELF_REFINEMENT_LOOP_SIGNALLED]
    payload: SelfRefinementLoopSignalledPayload


class MemoryIndexedPayload(BasePayload):
    """Audit record after a repo-scoped memory index rebuild."""

    repo_scope_hash: str = Field(min_length=8, max_length=64)
    generation_id: str = Field(min_length=8, max_length=64)
    chunks_added: int = Field(ge=0)
    chunks_skipped: int = Field(ge=0)
    embedding_mode: Literal["deterministic", "ollama"] = "deterministic"
    embedding_model_id: str = Field(min_length=1, max_length=128)
    index_dir: str | None = Field(default=None, max_length=512)


class MemoryIndexedEvent(BaseHermesEvent):
    event_type: Literal[EventType.MEMORY_INDEXED]
    payload: MemoryIndexedPayload


class MemoryRetrievalEmittedPayload(BasePayload):
    """Audit record when memory hits are injected into a stage."""

    stage_name: str = Field(min_length=1, max_length=256)
    query_digest: str = Field(min_length=8, max_length=64)
    hit_chunk_ids: list[str] = Field(default_factory=list, max_length=20)
    excerpt_chars: int = Field(ge=0)
    retrieval_k: int = Field(ge=0, le=20)
    repo_scope_hash: str = Field(min_length=8, max_length=64)
    generation_id: str | None = Field(default=None, max_length=64)


class MemoryRetrievalEmittedEvent(BaseHermesEvent):
    event_type: Literal[EventType.MEMORY_RETRIEVAL_EMITTED]
    payload: MemoryRetrievalEmittedPayload


HermesEventUnion: TypeAlias = (
    RunCreatedEvent
    | RunStartedEvent
    | RunFailedEvent
    | RunCompletedEvent
    | RunEscalatedEvent
    | ModelPreflightStartedEvent
    | ModelPreflightPassedEvent
    | ModelPreflightFailedEvent
    | ModelSelectedPrimaryEvent
    | ModelSelectedFallbackEvent
    | StageStartedEvent
    | StageBlockedEvent
    | StagePassedEvent
    | StageFailedEvent
    | CriticVerdictEmittedEvent
    | FindingCreatedEvent
    | FindingRoutedEvent
    | FindingClosedEvent
    | GateDecisionEmittedEvent
    | GateOverriddenEvent
    | PersonaShelfUpdatedEvent
    | SelfRefinementLoopSignalledEvent
    | MemoryIndexedEvent
    | MemoryRetrievalEmittedEvent
)

HermesEvent: TypeAlias = Annotated[HermesEventUnion, Field(discriminator="event_type")]

EventEnvelope: TypeAlias = HermesEvent

event_envelope_adapter: TypeAdapter[HermesEvent] = TypeAdapter(HermesEvent)


def validate_event_dict(
    data: object,
    *,
    context: dict[str, Any] | None = None,
) -> HermesEventUnion:
    """Parse and enforce event_type -> payload coupling.

    Pass ``context={finding_fix_strictness: FindingFixStrictnessSettings(...)}`` (or a dict with
    the same keys) to control when ``finding.created`` payloads must include ``required_fixes``.
    Omitted key uses ``DEFAULT_FINDING_FIX_STRICTNESS``.
    """
    merged: dict[str, Any] = dict(context or {})
    merged.setdefault(
        FINDING_FIX_STRICTNESS_CONTEXT_KEY,
        DEFAULT_FINDING_FIX_STRICTNESS,
    )
    return event_envelope_adapter.validate_python(data, context=merged)


def serialize_event_persistent(event: HermesEventUnion) -> dict[str, Any]:
    """JSON-shaped dict suitable for columns / payloads (aliases, enums as primitives)."""
    return event.model_dump(mode="json", by_alias=True)
