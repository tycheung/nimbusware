"""MVP run lifecycle: create → preflight → plan stage → writer loop.

Scraper or other roles that perform outbound HTTP should use
``nimbusware_executor.fetch.egress_checked_httpx_get`` with the frozen
``PolicySnapshot.network_egress`` fields (domain allowlist, scraper role UUIDs)
and the acting role id, instead of calling ``httpx`` directly.

Implementation is split under ``nimbusware_orchestrator._pipeline``; this module
remains the stable import and ``unittest.mock.patch`` target.
"""

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
