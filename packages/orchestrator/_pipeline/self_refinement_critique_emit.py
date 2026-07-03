from __future__ import annotations

from typing import Any
from uuid import UUID

from env.env_flags import env_truthy
from orchestrator._pipeline._helpers import (
    Verdict,
    emit_stub_self_refinement_critique_panel,
    execute_self_refinement_critique_llm,
    ollama_runtime_from_host,
    self_refinement_llm_critique_effective_for_run,
)


def try_emit_self_refinement_critique_for_host(
    host: Any,
    run_id: UUID,
    *,
    llm_critique_enabled: bool,
    gate_decision: str,
    workflow_profile: str | None,
    workflow_block: Any,
    evaluation_status: str,
    gaps: list[str],
    description: str,
) -> dict[str, Any]:
    if not (
        llm_critique_enabled
        and gate_decision == "hold"
        and self_refinement_llm_critique_effective_for_run(
            host._repo_root,
            workflow_profile,
            workflow_block,
            config_materializer=host._config_materializer,
        )
    ):
        return {}
    model = host._selected_model_for_run(run_id)
    if not model:
        return {}
    base_url, timeout = ollama_runtime_from_host(host)
    llm_result = execute_self_refinement_critique_llm(
        host._store,
        host._registry,
        host._critique_router,
        run_id=run_id,
        base_url=base_url,
        model_id=model,
        evaluation_status=evaluation_status,
        gaps=gaps,
        description=description,
        timeout_seconds=timeout,
    )
    if llm_result is not None:
        out: dict[str, Any] = {
            "orchestration_branch": "rules_with_llm_critique",
            "llm_critique_attempted": True,
            "llm_critique_verdict": Verdict(str(llm_result.get("verdict", "FAIL"))),
        }
        gate_raw = str(llm_result.get("gate_decision", "hold")).strip().lower()
        out["llm_gate_decision"] = "proceed" if gate_raw == "proceed" else "hold"
        summary_raw = llm_result.get("summary")
        if isinstance(summary_raw, str) and summary_raw.strip():
            out["llm_critique_summary"] = summary_raw.strip()[:500]
        return out
    if env_truthy("NIMBUSWARE_SELF_REFINEMENT_CRITIQUE_STUB"):
        emit_stub_self_refinement_critique_panel(
            host._store,
            host._registry,
            host._critique_router,
            run_id=run_id,
        )
    return {}
