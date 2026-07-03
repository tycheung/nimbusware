from __future__ import annotations

from orchestrator._pipeline.base import RunOrchestratorBase
from orchestrator._pipeline.stage_registry import PIPELINE_STAGE_MIXINS

_MIXINS = (*PIPELINE_STAGE_MIXINS, RunOrchestratorBase)


class RunOrchestrator(*_MIXINS):  # type: ignore[misc]
    """Event-sourced run pipeline composed from ordered stage mixins.

    Mixin order: ``orchestrator._pipeline.stage_registry.PIPELINE_STAGE_MIXINS``.
    """
