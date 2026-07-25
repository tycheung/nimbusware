"""Future orchestrator seam for broker-backed LLM (sak403-b; wiring in sak410).

Not called by production paths yet. Intended call sites when dual-run lands:

- ``orchestrator.routing.resolver.ModelBindingResolver`` chat / chat_json
- ``orchestrator.llm.common`` plan-patch helpers
- ``orchestrator.routing.preflight`` model resolution

When this returns ``"broker"``, stages should invoke SwissArmyNoife ``llm.chat``
via ``BrokerClient`` (HTTP admin) or MCP (``sak402``), with Python fallback on
broker errors per ``docs/dual-run-flags.md``.
"""

from __future__ import annotations

from broker_client.flags import LlmBackend, select_llm_backend


def select_llm_backend_for_stage(stage_name: str) -> LlmBackend:
    _ = stage_name
    return select_llm_backend()
