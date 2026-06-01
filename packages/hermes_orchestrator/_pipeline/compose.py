from __future__ import annotations

import functools
import types
from inspect import getattr_static

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


def _pipeline_module_globals() -> dict[str, object]:
    import hermes_orchestrator.pipeline as pipeline_module

    return pipeline_module.__dict__


def _bind_function(fn: types.FunctionType) -> types.FunctionType:
    """Wrap mixin callables so names resolve via ``hermes_orchestrator.pipeline``."""

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

    return wrapper  # type: ignore[return-value]


def _rebind_descriptor(name: str, attr: object, cls: type) -> None:
    if isinstance(attr, staticmethod):
        fn = attr.__func__
        setattr(cls, name, staticmethod(_bind_function(fn)))
        return
    if isinstance(attr, classmethod):
        fn = attr.__func__
        setattr(cls, name, classmethod(_bind_function(fn)))
        return
    if isinstance(attr, property):
        fget = _bind_function(attr.fget) if attr.fget is not None else None
        fset = _bind_function(attr.fset) if attr.fset is not None else None
        fdel = _bind_function(attr.fdel) if attr.fdel is not None else None
        setattr(cls, name, property(fget, fset, fdel))
        return
    if isinstance(attr, types.FunctionType):
        setattr(cls, name, _bind_function(attr))


def build_run_orchestrator_class(_pipeline_globals: dict[str, object]) -> type:
    """Build ``RunOrchestrator``; mixin methods resolve helpers via ``pipeline``."""
    del _pipeline_globals
    composed: type = type(
        "RunOrchestrator",
        _MIXINS,
        {
            "__doc__": (
                "MVP run lifecycle: create → preflight → plan stage → writer loop."
            ),
        },
    )
    for base in composed.__mro__:
        if base in {object, composed}:
            continue
        for name in base.__dict__:
            if name == "__init__" or (
                name.startswith("__") and name.endswith("__")
            ):
                continue
            try:
                raw = getattr_static(base, name)
            except AttributeError:
                continue
            _rebind_descriptor(name, raw, composed)
    return composed
