from __future__ import annotations

import functools
import types
from inspect import getattr_static
from typing import cast

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


def _pipeline_module_globals() -> dict[str, object]:
    import nimbusware_orchestrator.pipeline as pipeline_module

    return pipeline_module.__dict__


def _bind_function(fn: types.FunctionType) -> types.FunctionType:
    """Wrap mixin callables so names resolve via ``nimbusware_orchestrator.pipeline``."""

    @functools.wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> object:
        fn_globals = fn.__globals__
        pipeline_globals = _pipeline_module_globals()
        snapshot = dict(fn_globals)
        try:
            fn_globals.clear()
            fn_globals.update(pipeline_globals)
            return fn(*args, **kwargs)
        finally:
            fn_globals.clear()
            fn_globals.update(snapshot)

    return cast(types.FunctionType, wrapper)


def _rebind_descriptor(name: str, attr: object, cls: type[object]) -> None:
    if isinstance(attr, staticmethod):
        fn = cast(types.FunctionType, attr.__func__)
        setattr(cls, name, staticmethod(_bind_function(fn)))
        return
    if isinstance(attr, classmethod):
        fn = cast(types.FunctionType, attr.__func__)
        setattr(cls, name, classmethod(_bind_function(fn)))
        return
    if isinstance(attr, property):
        fget = _bind_function(attr.fget) if isinstance(attr.fget, types.FunctionType) else attr.fget
        fset = _bind_function(attr.fset) if isinstance(attr.fset, types.FunctionType) else attr.fset
        fdel = _bind_function(attr.fdel) if isinstance(attr.fdel, types.FunctionType) else attr.fdel
        setattr(cls, name, property(fget, fset, fdel))
        return
    if isinstance(attr, types.FunctionType):
        setattr(cls, name, _bind_function(attr))


class RunOrchestrator(
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
):
    """MVP run lifecycle: create → preflight → plan stage → writer loop."""


def _finalize_run_orchestrator_class(cls: type) -> type:
    for base in cls.__mro__:
        if base in {object, cls}:
            continue
        for name in base.__dict__:
            if name == "__init__" or (name.startswith("__") and name.endswith("__")):
                continue
            try:
                raw = getattr_static(base, name)
            except AttributeError:
                continue
            _rebind_descriptor(name, raw, cls)
    return cls


def build_run_orchestrator_class(_pipeline_globals: dict[str, object]) -> type[object]:
    del _pipeline_globals
    return _finalize_run_orchestrator_class(RunOrchestrator)
