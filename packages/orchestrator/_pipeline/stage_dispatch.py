"""Pipeline stage registry scaffold (documentation-only; mixins remain authoritative).

``PIPELINE_STAGES`` maps logical stage names to mixin classes from
``stage_registry.PIPELINE_STAGE_MIXINS``. Future work may dispatch through
``PipelineStage.run`` instead of MRO-composed mixins.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

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


@runtime_checkable
class PipelineStage(Protocol):
    name: str

    def run(self, host: Any, **kwargs: Any) -> None: ...


@dataclass(frozen=True)
class PipelineStageRegistration:
    """Documents one pipeline stage; ``run`` is not wired yet."""

    name: str
    mixin: type

    def run(self, host: Any, **kwargs: Any) -> None:
        msg = f"stage dispatch not implemented for {self.name!r}"
        raise NotImplementedError(msg)


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
