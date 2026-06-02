from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from agent_core.models.events_foundation import EventMetadata, EventType, RoleId
from agent_core.models.events_payloads import (
    DEFAULT_FINDING_FIX_STRICTNESS,
    FINDING_FIX_STRICTNESS_CONTEXT_KEY,
    CriticVerdictEmittedPayload,
    DomainCriticProposedPayload,
    FindingClosedPayload,
    FindingCreatedPayload,
    FindingRoutedPayload,
    GateDecisionEmittedPayload,
    GateOverriddenPayload,
    MemoryIndexedPayload,
    MemoryRetrievalEmittedPayload,
    ModelPreflightFailedPayload,
    ModelPreflightPassedPayload,
    ModelPreflightStartedPayload,
    ModelSelectedFallbackPayload,
    ModelSelectedPrimaryPayload,
    PersonaShelfUpdatedPayload,
    ResearchBriefEmittedPayload,
    ResearchPatternIndexedPayload,
    RunCompletedPayload,
    RunCreatedPayload,
    RunEscalatedPayload,
    RunFailedPayload,
    RunStartedPayload,
    SelfRefinementLoopSignalledPayload,
    StageBlockedPayload,
    StageFailedPayload,
    StagePassedPayload,
    StageStartedPayload,
    StitchAppliedPayload,
    StitchDependencyCheckedPayload,
    StitchFailedPayload,
    StitchLicenseCheckedPayload,
    StitchPlanEmittedPayload,
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


class PersonaShelfUpdatedEvent(BaseHermesEvent):
    event_type: Literal[EventType.PERSONA_SHELF_UPDATED]
    payload: PersonaShelfUpdatedPayload


class SelfRefinementLoopSignalledEvent(BaseHermesEvent):
    event_type: Literal[EventType.SELF_REFINEMENT_LOOP_SIGNALLED]
    payload: SelfRefinementLoopSignalledPayload


class MemoryIndexedEvent(BaseHermesEvent):
    event_type: Literal[EventType.MEMORY_INDEXED]
    payload: MemoryIndexedPayload


class MemoryRetrievalEmittedEvent(BaseHermesEvent):
    event_type: Literal[EventType.MEMORY_RETRIEVAL_EMITTED]
    payload: MemoryRetrievalEmittedPayload


class ResearchBriefEmittedEvent(BaseHermesEvent):
    event_type: Literal[EventType.RESEARCH_BRIEF_EMITTED]
    payload: ResearchBriefEmittedPayload


class ResearchPatternIndexedEvent(BaseHermesEvent):
    event_type: Literal[EventType.RESEARCH_PATTERN_INDEXED]
    payload: ResearchPatternIndexedPayload


class DomainCriticProposedEvent(BaseHermesEvent):
    event_type: Literal[EventType.DOMAIN_CRITIC_PROPOSED]
    payload: DomainCriticProposedPayload


class StitchLicenseCheckedEvent(BaseHermesEvent):
    event_type: Literal[EventType.STITCH_LICENSE_CHECKED]
    payload: StitchLicenseCheckedPayload


class StitchDependencyCheckedEvent(BaseHermesEvent):
    event_type: Literal[EventType.STITCH_DEPENDENCY_CHECKED]
    payload: StitchDependencyCheckedPayload


class StitchPlanEmittedEvent(BaseHermesEvent):
    event_type: Literal[EventType.STITCH_PLAN_EMITTED]
    payload: StitchPlanEmittedPayload


class StitchAppliedEvent(BaseHermesEvent):
    event_type: Literal[EventType.STITCH_APPLIED]
    payload: StitchAppliedPayload


class StitchFailedEvent(BaseHermesEvent):
    event_type: Literal[EventType.STITCH_FAILED]
    payload: StitchFailedPayload


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
    | ResearchBriefEmittedEvent
    | ResearchPatternIndexedEvent
    | DomainCriticProposedEvent
    | StitchLicenseCheckedEvent
    | StitchDependencyCheckedEvent
    | StitchPlanEmittedEvent
    | StitchAppliedEvent
    | StitchFailedEvent
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
