from __future__ import annotations

from hermes_orchestrator._pipeline.base import RunOrchestratorBase
from hermes_orchestrator._pipeline.create_run import CreateRunMixin
from hermes_orchestrator._pipeline.critique_gates import CritiqueGatesMixin
from hermes_orchestrator._pipeline.escalation import EscalationMixin
from hermes_orchestrator._pipeline.lifecycle import LifecycleMixin
from hermes_orchestrator._pipeline.micro_slice import MicroSliceMixin
from hermes_orchestrator._pipeline.optional_critique import OptionalCritiqueMixin
from hermes_orchestrator._pipeline.optional_stages import OptionalStagesMixin
from hermes_orchestrator._pipeline.pipeline_scraper import PipelineScraperMixin
from hermes_orchestrator._pipeline.writers import WritersMixin

_MIXINS = (
    CreateRunMixin,
    MicroSliceMixin,
    PipelineScraperMixin,
    LifecycleMixin,
    CritiqueGatesMixin,
    WritersMixin,
    OptionalCritiqueMixin,
    EscalationMixin,
    OptionalStagesMixin,
    RunOrchestratorBase,
)


def build_run_orchestrator_class(_pipeline_globals: dict[str, object]) -> type:
    """Build ``RunOrchestrator`` from mixins in explicit MRO order."""
    del _pipeline_globals
    return type(
        "RunOrchestrator",
        _MIXINS,
        {
            "__doc__": (
                "MVP run lifecycle: create → preflight → plan stage → writer loop."
            ),
        },
    )
