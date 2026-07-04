from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from agent_core.models.events_foundation import EventMetadata, EventType, RoleId
from agent_core.models.events_payloads import (
    DEFAULT_FINDING_FIX_STRICTNESS,
    FINDING_FIX_STRICTNESS_CONTEXT_KEY,
    CampaignCompletedPayload,
    CampaignCreatedPayload,
    CampaignFailedPayload,
    CampaignPausedPayload,
    CompletionEvaluatedPayload,
    ContextBudgetSampledPayload,
    CriticVerdictEmittedPayload,
    DeliveryBacklogGeneratedPayload,
    DeliveryBacklogRevisedPayload,
    DomainCriticProposedPayload,
    EpicStatusChangedPayload,
    FindingClosedPayload,
    FindingCreatedPayload,
    FindingRoutedPayload,
    GateDecisionEmittedPayload,
    GateOverriddenPayload,
    HardwareProfileDetectedPayload,
    MaintenanceArchitecturePassedPayload,
    MaintenanceArchitectureStartedPayload,
    MaintenanceRefactorPassedPayload,
    MaintenanceRefactorStartedPayload,
    MemoryIndexedPayload,
    MemoryRetrievalEmittedPayload,
    ModelBindingOverriddenPayload,
    ModelPreflightFailedPayload,
    ModelPreflightPassedPayload,
    ModelPreflightStartedPayload,
    ModelSelectedFallbackPayload,
    ModelSelectedPrimaryPayload,
    PersonaShelfUpdatedPayload,
    ResearchBriefEmittedPayload,
    ResearchBriefReviewPayload,
    ResearchPatternIndexedPayload,
    ResourcePressureWarnPayload,
    RunCompletedPayload,
    RunCreatedPayload,
    RunEscalatedPayload,
    RunFailedPayload,
    RunStartedPayload,
    SelfRefinementLoopSignalledPayload,
    SliceDeferredPayload,
    SliceQueuedPayload,
    StageBlockedPayload,
    StageFailedPayload,
    StagePassedPayload,
    StageStartedPayload,
    StitchAppliedPayload,
    StitchDependencyCheckedPayload,
    StitchFailedPayload,
    StitchLicenseCheckedPayload,
    StitchPlanEmittedPayload,
    WorkloadRoleClaimedPayload,
    WorkloadRoleReleasedPayload,
)


class BaseNimbuswareEvent(BaseModel):
    """Shared envelope fields (DB assigns store_seq separately at persist time).

    ``actor_role`` is a Role Registry UUID when set.
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


class RunCreatedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.RUN_CREATED]
    payload: RunCreatedPayload


class RunStartedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.RUN_STARTED]
    payload: RunStartedPayload


class RunFailedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.RUN_FAILED]
    payload: RunFailedPayload


class RunCompletedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.RUN_COMPLETED]
    payload: RunCompletedPayload


class RunEscalatedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.RUN_ESCALATED]
    payload: RunEscalatedPayload


class GateOverriddenEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.GATE_OVERRIDDEN]
    payload: GateOverriddenPayload


class ModelPreflightStartedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.MODEL_PREFLIGHT_STARTED]
    payload: ModelPreflightStartedPayload


class ModelPreflightPassedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.MODEL_PREFLIGHT_PASSED]
    payload: ModelPreflightPassedPayload


class ModelPreflightFailedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.MODEL_PREFLIGHT_FAILED]
    payload: ModelPreflightFailedPayload


class ModelSelectedPrimaryEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.MODEL_SELECTED_PRIMARY]
    payload: ModelSelectedPrimaryPayload


class ModelSelectedFallbackEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.MODEL_SELECTED_FALLBACK]
    payload: ModelSelectedFallbackPayload


class ModelBindingOverriddenEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.MODEL_BINDING_OVERRIDDEN]
    payload: ModelBindingOverriddenPayload


class WorkloadRoleClaimedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.WORKLOAD_ROLE_CLAIMED]
    payload: WorkloadRoleClaimedPayload


class WorkloadRoleReleasedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.WORKLOAD_ROLE_RELEASED]
    payload: WorkloadRoleReleasedPayload


class StageStartedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.STAGE_STARTED]
    payload: StageStartedPayload


class StageBlockedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.STAGE_BLOCKED]
    payload: StageBlockedPayload


class StagePassedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.STAGE_PASSED]
    payload: StagePassedPayload


class StageFailedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.STAGE_FAILED]
    payload: StageFailedPayload


class CriticVerdictEmittedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.CRITIC_VERDICT_EMITTED]
    payload: CriticVerdictEmittedPayload


class FindingCreatedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.FINDING_CREATED]
    payload: FindingCreatedPayload


class FindingRoutedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.FINDING_ROUTED]
    payload: FindingRoutedPayload


class FindingClosedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.FINDING_CLOSED]
    payload: FindingClosedPayload


class GateDecisionEmittedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.GATE_DECISION_EMITTED]
    payload: GateDecisionEmittedPayload


class PersonaShelfUpdatedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.PERSONA_SHELF_UPDATED]
    payload: PersonaShelfUpdatedPayload


class SelfRefinementLoopSignalledEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.SELF_REFINEMENT_LOOP_SIGNALLED]
    payload: SelfRefinementLoopSignalledPayload


class MemoryIndexedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.MEMORY_INDEXED]
    payload: MemoryIndexedPayload


class MemoryRetrievalEmittedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.MEMORY_RETRIEVAL_EMITTED]
    payload: MemoryRetrievalEmittedPayload


class ResearchBriefEmittedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.RESEARCH_BRIEF_EMITTED]
    payload: ResearchBriefEmittedPayload


class ResearchBriefApprovedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.RESEARCH_BRIEF_APPROVED]
    payload: ResearchBriefReviewPayload


class ResearchBriefRejectedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.RESEARCH_BRIEF_REJECTED]
    payload: ResearchBriefReviewPayload


class ResearchPatternIndexedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.RESEARCH_PATTERN_INDEXED]
    payload: ResearchPatternIndexedPayload


class DomainCriticProposedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.DOMAIN_CRITIC_PROPOSED]
    payload: DomainCriticProposedPayload


class StitchLicenseCheckedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.STITCH_LICENSE_CHECKED]
    payload: StitchLicenseCheckedPayload


class StitchDependencyCheckedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.STITCH_DEPENDENCY_CHECKED]
    payload: StitchDependencyCheckedPayload


class StitchPlanEmittedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.STITCH_PLAN_EMITTED]
    payload: StitchPlanEmittedPayload


class StitchAppliedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.STITCH_APPLIED]
    payload: StitchAppliedPayload


class StitchFailedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.STITCH_FAILED]
    payload: StitchFailedPayload


class HardwareProfileDetectedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.HARDWARE_PROFILE_DETECTED]
    payload: HardwareProfileDetectedPayload


class ResourcePressureWarnEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.RESOURCE_PRESSURE_WARN]
    payload: ResourcePressureWarnPayload


class ContextBudgetSampledEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.CONTEXT_BUDGET_SAMPLED]
    payload: ContextBudgetSampledPayload


class CampaignCreatedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.CAMPAIGN_CREATED]
    payload: CampaignCreatedPayload


class CampaignCompletedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.CAMPAIGN_COMPLETED]
    payload: CampaignCompletedPayload


class CampaignFailedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.CAMPAIGN_FAILED]
    payload: CampaignFailedPayload


class CampaignPausedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.CAMPAIGN_PAUSED]
    payload: CampaignPausedPayload


class DeliveryBacklogGeneratedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.DELIVERY_BACKLOG_GENERATED]
    payload: DeliveryBacklogGeneratedPayload


class DeliveryBacklogRevisedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.DELIVERY_BACKLOG_REVISED]
    payload: DeliveryBacklogRevisedPayload


class EpicStatusChangedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.EPIC_STATUS_CHANGED]
    payload: EpicStatusChangedPayload


class SliceQueuedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.SLICE_QUEUED]
    payload: SliceQueuedPayload


class SliceDeferredEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.SLICE_DEFERRED]
    payload: SliceDeferredPayload


class MaintenanceRefactorStartedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.MAINTENANCE_REFACTOR_STARTED]
    payload: MaintenanceRefactorStartedPayload


class MaintenanceRefactorPassedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.MAINTENANCE_REFACTOR_PASSED]
    payload: MaintenanceRefactorPassedPayload


class MaintenanceArchitectureStartedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.MAINTENANCE_ARCHITECTURE_STARTED]
    payload: MaintenanceArchitectureStartedPayload


class MaintenanceArchitecturePassedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.MAINTENANCE_ARCHITECTURE_PASSED]
    payload: MaintenanceArchitecturePassedPayload


class CompletionEvaluatedEvent(BaseNimbuswareEvent):
    event_type: Literal[EventType.COMPLETION_EVALUATED]
    payload: CompletionEvaluatedPayload


NimbuswareEventUnion: TypeAlias = (
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
    | ModelBindingOverriddenEvent
    | WorkloadRoleClaimedEvent
    | WorkloadRoleReleasedEvent
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
    | ResearchBriefApprovedEvent
    | ResearchBriefRejectedEvent
    | ResearchPatternIndexedEvent
    | DomainCriticProposedEvent
    | StitchLicenseCheckedEvent
    | StitchDependencyCheckedEvent
    | StitchPlanEmittedEvent
    | StitchAppliedEvent
    | StitchFailedEvent
    | HardwareProfileDetectedEvent
    | ResourcePressureWarnEvent
    | ContextBudgetSampledEvent
    | CampaignCreatedEvent
    | CampaignCompletedEvent
    | CampaignFailedEvent
    | CampaignPausedEvent
    | DeliveryBacklogGeneratedEvent
    | DeliveryBacklogRevisedEvent
    | EpicStatusChangedEvent
    | SliceQueuedEvent
    | SliceDeferredEvent
    | MaintenanceRefactorStartedEvent
    | MaintenanceRefactorPassedEvent
    | MaintenanceArchitectureStartedEvent
    | MaintenanceArchitecturePassedEvent
    | CompletionEvaluatedEvent
)

NimbuswareEvent: TypeAlias = Annotated[NimbuswareEventUnion, Field(discriminator="event_type")]

EventEnvelope: TypeAlias = NimbuswareEvent

event_envelope_adapter: TypeAdapter[NimbuswareEvent] = TypeAdapter(NimbuswareEvent)


def validate_event_dict(
    data: object,
    *,
    context: dict[str, Any] | None = None,
) -> NimbuswareEventUnion:
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


def serialize_event_persistent(event: NimbuswareEventUnion) -> dict[str, Any]:
    """JSON-shaped dict suitable for columns / payloads (aliases, enums as primitives)."""
    return event.model_dump(mode="json", by_alias=True)
