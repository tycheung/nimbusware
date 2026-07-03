from __future__ import annotations

from orchestrator._pipeline.base import RunOrchestratorBase
from orchestrator._pipeline.stage_registry import PIPELINE_STAGE_MIXINS

RunOrchestrator = type(
    "RunOrchestrator",
    (*PIPELINE_STAGE_MIXINS, RunOrchestratorBase),
    {
        "__doc__": (
            "Event-sourced run pipeline composed from ordered stage mixins "
            "(see orchestrator._pipeline.stage_registry.PIPELINE_STAGE_MIXINS)."
        ),
    },
)
