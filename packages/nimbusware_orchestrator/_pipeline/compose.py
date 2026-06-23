from __future__ import annotations

from nimbusware_orchestrator._pipeline.base import RunOrchestratorBase
from nimbusware_orchestrator._pipeline.campaign_dispatch import CampaignDispatchMixin
from nimbusware_orchestrator._pipeline.create_run import CreateRunMixin
from nimbusware_orchestrator._pipeline.critique_gates import CritiqueGatesMixin
from nimbusware_orchestrator._pipeline.escalation import EscalationMixin
from nimbusware_orchestrator._pipeline.lifecycle import LifecycleMixin
from nimbusware_orchestrator._pipeline.micro_slice import MicroSliceMixin
from nimbusware_orchestrator._pipeline.optional_critique import OptionalCritiqueMixin
from nimbusware_orchestrator._pipeline.optional_stages import OptionalStagesMixin
from nimbusware_orchestrator._pipeline.optional_stages_research import ResearchOptionalStagesMixin
from nimbusware_orchestrator._pipeline.optional_stages_stitch import StitchOptionalStagesMixin
from nimbusware_orchestrator._pipeline.pipeline_scraper import PipelineScraperMixin
from nimbusware_orchestrator._pipeline.role_execute import RoleExecuteMixin
from nimbusware_orchestrator._pipeline.writers import WritersMixin

_MIXINS = (
    CreateRunMixin,
    CampaignDispatchMixin,
    MicroSliceMixin,
    PipelineScraperMixin,
    LifecycleMixin,
    CritiqueGatesMixin,
    WritersMixin,
    OptionalCritiqueMixin,
    EscalationMixin,
    OptionalStagesMixin,
    ResearchOptionalStagesMixin,
    StitchOptionalStagesMixin,
    RoleExecuteMixin,
    RunOrchestratorBase,
)


class RunOrchestrator(*_MIXINS):  # type: ignore[misc]
    pass
