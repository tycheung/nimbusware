"""Pipeline stage registry: maps logical stage names to mixin classes.

Mixins remain authoritative for execution via MRO composition on ``RunOrchestrator``.
"""

from __future__ import annotations

from dataclasses import dataclass

from orchestrator._pipeline.campaign_dispatch import CampaignDispatchMixin
from orchestrator._pipeline.create_run import CreateRunMixin
from orchestrator._pipeline.critique_gates import CritiqueGatesMixin
from orchestrator._pipeline.escalation import EscalationMixin
from orchestrator._pipeline.lifecycle import LifecycleMixin
from orchestrator._pipeline.micro_slice import MicroSliceMixin
from orchestrator._pipeline.optional_critique import OptionalCritiqueMixin
from orchestrator._pipeline.optional_stages import OptionalStagesMixin
from orchestrator._pipeline.optional_stages_research import ResearchOptionalStagesMixin
from orchestrator._pipeline.optional_stages_stitch import StitchOptionalStagesMixin
from orchestrator._pipeline.pipeline_scraper import PipelineScraperMixin
from orchestrator._pipeline.role_execute import RoleExecuteMixin
from orchestrator._pipeline.writers import WritersMixin


@dataclass(frozen=True)
class PipelineStageRegistration:
    name: str
    mixin: type


PIPELINE_STAGES: tuple[PipelineStageRegistration, ...] = (
    PipelineStageRegistration("create_run", CreateRunMixin),
    PipelineStageRegistration("campaign_dispatch", CampaignDispatchMixin),
    PipelineStageRegistration("micro_slice", MicroSliceMixin),
    PipelineStageRegistration("pipeline_scraper", PipelineScraperMixin),
    PipelineStageRegistration("lifecycle", LifecycleMixin),
    PipelineStageRegistration("critique_gates", CritiqueGatesMixin),
    PipelineStageRegistration("writers", WritersMixin),
    PipelineStageRegistration("optional_critique", OptionalCritiqueMixin),
    PipelineStageRegistration("escalation", EscalationMixin),
    PipelineStageRegistration("optional_stages", OptionalStagesMixin),
    PipelineStageRegistration("research_optional_stages", ResearchOptionalStagesMixin),
    PipelineStageRegistration("stitch_optional_stages", StitchOptionalStagesMixin),
    PipelineStageRegistration("role_execute", RoleExecuteMixin),
)
