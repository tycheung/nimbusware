"""Ordered pipeline stage mixins for RunOrchestrator."""

from __future__ import annotations

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

PIPELINE_STAGE_MIXINS: tuple[type, ...] = (
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
)


def build_run_orchestrator_base(*extra_bases: type) -> tuple[type, ...]:
    return (*PIPELINE_STAGE_MIXINS, *extra_bases)
