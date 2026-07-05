from __future__ import annotations

from orchestrator._pipeline.stage_dispatch import (
    PIPELINE_STAGES,
    PipelineStageRegistration,
)

PIPELINE_STAGE_MIXINS: tuple[type, ...] = tuple(entry.mixin for entry in PIPELINE_STAGES)


def build_run_orchestrator_base(*extra_bases: type) -> tuple[type, ...]:
    return (*PIPELINE_STAGE_MIXINS, *extra_bases)


__all__ = (
    "PIPELINE_STAGE_MIXINS",
    "PIPELINE_STAGES",
    "PipelineStageRegistration",
    "build_run_orchestrator_base",
)
