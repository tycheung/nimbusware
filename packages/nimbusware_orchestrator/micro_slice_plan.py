from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType
from nimbusware_env.env_flags import nimbusware_use_llm_enabled
from nimbusware_orchestrator.llm_slice import execute_slice_plan_llm
from nimbusware_orchestrator.micro_slice import SlicePlan, parse_slice_plan

if TYPE_CHECKING:
    from nimbusware_orchestrator.pipeline import RunOrchestrator


def default_stub_slice_plan(slice_index: int) -> SlicePlan:
    return parse_slice_plan(
        {
            "slice_id": f"slice-{slice_index}",
            "rationale": "Conservative default micro-slice for automated verify pass",
            "target_paths": [
                "packages/nimbusware_orchestrator/micro_slice.py",
                "packages/nimbusware_orchestrator/slice_gate.py",
            ],
            "acceptance_criteria": "Scoped unit tests pass",
        },
    )


def custom_agent_system_prompt(orch: RunOrchestrator, rows: list[dict[str, Any]]) -> str | None:
    from nimbusware_config.persist import load_custom_agent_registry

    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        agent = mapping_or_empty(mapping_or_empty(row.get("metadata")).get("custom_agent"))
        if agent.get("id"):
            reg = load_custom_agent_registry(
                orch.repo_root,
                materializer=orch.config_materializer,
            )
            full = reg.get(str(agent["id"]))
            if full is not None:
                return full.system_prompt
        break
    return None


def plan_one_slice(
    orch: RunOrchestrator,
    run_id: UUID,
    *,
    slice_index: int,
    budget_feedback: str | None = None,
) -> SlicePlan:
    rows = orch._store.list_run_events(str(run_id))
    memory_excerpt = ""
    run_meta = orch._run_created_metadata(run_id)
    from nimbusware_orchestrator.workflow_memory import (
        memory_settings_from_run_metadata,
        retrieve_memory_excerpt_for_slice,
        run_memory_retrieval_enabled,
    )

    if run_memory_retrieval_enabled(run_meta) and orch._memory_chunk_store is not None:
        settings = memory_settings_from_run_metadata(run_meta)
        stub = default_stub_slice_plan(slice_index)
        memory_excerpt, _, _ = retrieve_memory_excerpt_for_slice(
            orch._memory_chunk_store,
            stub,
            repo_root=orch.repo_root,
            settings=settings,
        )
    if nimbusware_use_llm_enabled():
        runtime = mapping_or_empty(orch._base_cfg().get("runtime"))
        model = orch._selected_model_for_run(run_id)
        if model:
            plan = execute_slice_plan_llm(
                rows=rows,
                base_url=str(runtime.get("base_url", "http://localhost:11434")),
                model_id=model,
                slice_index=slice_index,
                timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                system_prompt=custom_agent_system_prompt(orch, rows),
                budget_feedback=budget_feedback,
                memory_excerpt=memory_excerpt,
            )
            if plan is not None:
                return plan
    from nimbusware_maker.workspace import resolve_run_workspace
    from nimbusware_orchestrator.patch_context import patch_slice_plan_for_run

    ws = resolve_run_workspace(rows)
    if ws is not None:
        patch_plan = patch_slice_plan_for_run(slice_index, rows, ws)
        if patch_plan is not None:
            return patch_plan
    return default_stub_slice_plan(slice_index)
