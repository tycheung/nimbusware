from __future__ import annotations

from orchestrator._pipeline import _helpers
from orchestrator._pipeline.compose import RunOrchestrator
from orchestrator._pipeline.dev_factory import default_paths, make_dev_orchestrator

for _name, _value in vars(_helpers).items():
    if _name.startswith("__"):
        continue
    globals()[_name] = _value

from orchestrator.routing.preflight import (  # noqa: E402
    build_binding_preflight_report,
    cloud_only_roles_satisfied,
)

globals()["build_binding_preflight_report"] = build_binding_preflight_report
globals()["cloud_only_roles_satisfied"] = cloud_only_roles_satisfied

__all__ = [
    "RunOrchestrator",
    "default_paths",
    "make_dev_orchestrator",
]
