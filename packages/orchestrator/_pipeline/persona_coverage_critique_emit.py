from __future__ import annotations

from typing import Any
from uuid import UUID

from orchestrator._pipeline._helpers import (
    emit_stub_persona_coverage_critique_panel,
    execute_persona_coverage_critique_llm,
    ollama_runtime_from_host,
    persona_coverage_critique_effective,
    persona_coverage_critique_llm_branch_effective,
)


def emit_persona_coverage_critique_optional_for_host(
    host: Any,
    run_id: UUID,
    *,
    block: Any,
    rules_eval: dict[str, Any],
    unanimous_gate_enforce: bool,
) -> None:
    if not persona_coverage_critique_effective(block):
        return
    emitted = False
    if persona_coverage_critique_llm_branch_effective(block):
        model = host._selected_model_for_run(run_id)
        if model:
            base_url, timeout = ollama_runtime_from_host(host)
            emitted = execute_persona_coverage_critique_llm(
                host._store,
                host._registry,
                host._critique_router,
                run_id=run_id,
                rules_eval=rules_eval,
                base_url=base_url,
                model_id=model,
                timeout_seconds=timeout,
                unanimous_gate_enforce=unanimous_gate_enforce,
            )
    if not emitted and block.persona_coverage_critique.stub:
        emit_stub_persona_coverage_critique_panel(
            host._store,
            host._registry,
            host._critique_router,
            run_id=run_id,
            rules_eval=rules_eval,
            unanimous_gate_enforce=unanimous_gate_enforce,
        )
