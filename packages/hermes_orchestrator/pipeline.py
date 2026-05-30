"""MVP run lifecycle: create → preflight → plan stage → writer loop.

Scraper or other roles that perform outbound HTTP should use
``hermes_executor.fetch.egress_checked_httpx_get`` with the frozen
``PolicySnapshot.network_egress`` fields (domain allowlist, scraper role UUIDs)
and the acting role id, instead of calling ``httpx`` directly.

Implementation is split under ``hermes_orchestrator._pipeline``; this module
remains the stable import and ``unittest.mock.patch`` target.
"""

from __future__ import annotations

from hermes_orchestrator._pipeline import _helpers
from hermes_orchestrator._pipeline.compose import build_run_orchestrator_class
from hermes_orchestrator._pipeline.dev_factory import default_paths, make_dev_orchestrator

for _name, _value in vars(_helpers).items():
    if _name.startswith("__"):
        continue
    globals()[_name] = _value

RunOrchestrator = build_run_orchestrator_class(globals())

__all__ = [
    "RunOrchestrator",
    "default_paths",
    "make_dev_orchestrator",
]
