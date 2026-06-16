from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from nimbusware_orchestrator.workflow_universal_critique import EffectiveUniversalCritique


@dataclass(frozen=True)
class RoleCritiqueEmitSpec:
    enabled: Callable[[EffectiveUniversalCritique], bool]
    llm: Callable[[EffectiveUniversalCritique], bool]
    stub: Callable[[EffectiveUniversalCritique], bool]
    execute_llm: Callable[..., bool]
    emit_stub: Callable[..., None]
    pre_emit: Callable[[Any, UUID], None] | None = None


def emit_role_critique_optional(
    host: Any,
    run_id: UUID,
    *,
    eff: EffectiveUniversalCritique,
    spec: RoleCritiqueEmitSpec,
    verifier_exit_code: int,
    log_snippet: str,
    ollama_runtime_from_host: Callable[..., tuple[str, float]],
) -> None:
    if not spec.enabled(eff):
        return
    if spec.pre_emit is not None:
        spec.pre_emit(host, run_id)
    emitted_llm = False
    if spec.llm(eff):
        model = host._selected_model_for_run(run_id)
        if model:
            base_url, timeout = ollama_runtime_from_host(host)
            emitted_llm = spec.execute_llm(
                host._store,
                host._registry,
                host._critique_router,
                run_id=run_id,
                base_url=base_url,
                model_id=model,
                verifier_exit_code=verifier_exit_code,
                log_snippet=log_snippet,
                timeout_seconds=timeout,
            )
    if not emitted_llm and spec.stub(eff):
        spec.emit_stub(
            host._store,
            host._registry,
            host._critique_router,
            run_id=run_id,
        )


def emit_role_critique_optional_for_host(
    host: Any,
    run_id: UUID,
    *,
    eff: EffectiveUniversalCritique,
    spec: RoleCritiqueEmitSpec,
    verifier_exit_code: int,
    log_snippet: str,
) -> None:
    from nimbusware_orchestrator._pipeline._helpers import ollama_runtime_from_host

    emit_role_critique_optional(
        host,
        run_id,
        eff=eff,
        spec=spec,
        verifier_exit_code=verifier_exit_code,
        log_snippet=log_snippet,
        ollama_runtime_from_host=ollama_runtime_from_host,
    )
