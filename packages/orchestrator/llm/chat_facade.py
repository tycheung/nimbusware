"""Broker-first chat helpers after sak411 (replaces orchestrator.llm.common chat path)."""

from __future__ import annotations

from typing import Any

from orchestrator.llm.broker_bridge import try_broker_chat_json

_STRICT_BROKER_MISS = "broker_miss: chat_facade: LLM unavailable under NIMBUSWARE_BROKER_LLM=1|2"


def _local_chat_json_via_plan_patch(
    *,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_seconds: float = 120.0,
    stage_name: str | None = None,
    agent_role: str | None = None,
    cache_blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    role = (agent_role or "").strip() or None
    if not role and stage_name:
        from orchestrator.model_routing.preflight import agent_role_for_stage

        role = agent_role_for_stage(stage_name)
    if role:
        from env import find_repo_root
        from orchestrator.collab.mesh_context import (
            mesh_actor_user_id,
            mesh_participant_overrides,
        )
        from orchestrator.collab.mesh_hydrate import ensure_mesh_binding_for_llm
        from orchestrator.model_routing.resolver import ModelBindingResolver

        ensure_mesh_binding_for_llm()
        resolver = ModelBindingResolver(find_repo_root())
        return resolver.chat_json(
            role,
            messages=messages,
            timeout_seconds=timeout_seconds,
            participant_overrides=mesh_participant_overrides(),
            actor_user_id=mesh_actor_user_id(),
            cache_blocks=cache_blocks,
            stage_name=stage_name,
        )
    if stage_name:
        from config.persist import load_model_routing_dict
        from env import find_repo_root
        from orchestrator.provider_routing_facade import (
            cloud_chat_json,
            resolve_stage_provider,
        )

        routing = load_model_routing_dict(find_repo_root())
        if resolve_stage_provider(routing, stage_name) == "cloud":
            return cloud_chat_json(
                routing,
                messages=messages,
                timeout_seconds=timeout_seconds,
                cache_blocks=cache_blocks,
                stage_name=stage_name or "",
            )
    from orchestrator.model_routing import chat as _ollama_chat_mod

    return _ollama_chat_mod.ollama_chat_json(
        base_url=base_url,
        model=model,
        messages=messages,
        timeout_seconds=timeout_seconds,
    )


def ollama_chat_json_via_plan_patch(
    *,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_seconds: float = 120.0,
    stage_name: str | None = None,
    agent_role: str | None = None,
    cache_blocks: list[dict[str, Any]] | None = None,
    peel_strict: bool = False,
) -> dict[str, Any]:
    if peel_strict:
        from broker_client.dual_run_route import try_or_refuse
        from broker_client.flags import broker_llm_enabled, broker_llm_only

        def _strict_broker_chat() -> dict[str, Any]:
            broker = try_broker_chat_json(list(messages), model=model)
            if broker is not None:
                return broker
            raise RuntimeError("broker miss")

        # sak492-d: Maker-critical stages refuse resolver/ollama fallback under LLM=1|2.
        hit = try_or_refuse(
            _strict_broker_chat,
            enabled=broker_llm_enabled,
            broker_only=broker_llm_only,
            msg=_STRICT_BROKER_MISS,
        )
        if hit is not None:
            return hit
        return _local_chat_json_via_plan_patch(
            base_url=base_url,
            model=model,
            messages=messages,
            timeout_seconds=timeout_seconds,
            stage_name=stage_name,
            agent_role=agent_role,
            cache_blocks=cache_blocks,
        )

    broker = try_broker_chat_json(list(messages), model=model)
    if broker is not None:
        return broker
    return _local_chat_json_via_plan_patch(
        base_url=base_url,
        model=model,
        messages=messages,
        timeout_seconds=timeout_seconds,
        stage_name=stage_name,
        agent_role=agent_role,
        cache_blocks=cache_blocks,
    )
