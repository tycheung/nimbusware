from __future__ import annotations

from nimbusware_orchestrator._pipeline import _helpers
from nimbusware_orchestrator._pipeline.compose import (
    RunOrchestrator,
    _finalize_run_orchestrator_class,
)
from nimbusware_orchestrator._pipeline.dev_factory import default_paths, make_dev_orchestrator

for _name, _value in vars(_helpers).items():
    if _name.startswith("__"):
        continue
    globals()[_name] = _value

_finalize_run_orchestrator_class(RunOrchestrator)

__all__ = [
    "RunOrchestrator",
    "default_paths",
    "make_dev_orchestrator",
]
