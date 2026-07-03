from __future__ import annotations

from orchestrator._pipeline.base import RunOrchestratorBase
from orchestrator._pipeline.stage_registry import PIPELINE_STAGE_MIXINS

_MIXINS = (*PIPELINE_STAGE_MIXINS, RunOrchestratorBase)


class RunOrchestrator(*_MIXINS):  # type: ignore[misc]
    pass
