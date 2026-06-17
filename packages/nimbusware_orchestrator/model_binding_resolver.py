"""Per-role model binding resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from agent_core.mapping import mapping_or_empty
from nimbusware_config.persist import load_model_routing_dict
from nimbusware_orchestrator.hybrid_routing import resolve_stage_provider
from nimbusware_orchestrator.llm.providers import provider_for_preset


@dataclass(frozen=True)
class ResolvedBinding:
    agent_role: str
    provider_kind: str
    provider_id: str
    model_id: str
    base_url: str | None
    api_key_ref: str | None
    connection_id: str | None
    binding_source: str
    params: dict[str, Any]


def _load_defaults_yaml(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "configs" / "model_bindings" / "defaults.yaml"
    if not path.is_file():
        return {"version": 1, "roles": {}}
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {"version": 1, "roles": {}}


def _binding_from_block(agent_role: str, block: dict[str, Any], *, source: str) -> ResolvedBinding:
    return ResolvedBinding(
        agent_role=agent_role,
        provider_kind=str(block.get("provider_kind") or "local"),
        provider_id=str(block.get("provider_id") or "ollama"),
        model_id=str(block.get("model_id") or ""),
        base_url=block.get("base_url"),
        api_key_ref=block.get("api_key_ref"),
        connection_id=block.get("connection_id"),
        binding_source=source,
        params=dict(mapping_or_empty(block.get("params"))),
    )


def _global_fallback(repo_root: Path, agent_role: str) -> ResolvedBinding:
    routing = load_model_routing_dict(repo_root)
    models = mapping_or_empty(routing.get("models"))
    primary = mapping_or_empty(models.get("primary"))
    model_id = str(primary.get("id") or "llama3.1:8b")
    runtime = mapping_or_empty(routing.get("runtime"))
    base_url = runtime.get("base_url")
    return ResolvedBinding(
        agent_role=agent_role,
        provider_kind="local",
        provider_id="ollama",
        model_id=model_id,
        base_url=str(base_url) if base_url else None,
        api_key_ref=None,
        connection_id=None,
        binding_source="model-routing.primary",
        params={},
    )


_ROLE_STAGE_MAP: dict[str, str] = {
    "planner": "plan",
    "backend_writer": "implement",
    "security_critic": "critique",
    "frontend_writer": "implement",
}


def _hybrid_routing_binding(repo_root: Path, agent_role: str) -> ResolvedBinding | None:
    """Map legacy stage_providers + cloud_runtime to per-role bindings."""
    routing = load_model_routing_dict(repo_root)
    stage = _ROLE_STAGE_MAP.get(agent_role)
    if not stage:
        return None
    if resolve_stage_provider(routing, stage) != "cloud":
        return None
    cloud = mapping_or_empty(routing.get("cloud_runtime"))
    if not cloud.get("enabled"):
        return None
    return ResolvedBinding(
        agent_role=agent_role,
        provider_kind="cloud",
        provider_id=str(cloud.get("provider") or "openai_compatible"),
        model_id=str(cloud.get("model_id") or "gpt-4o-mini"),
        base_url=str(cloud.get("base_url") or "") or None,
        api_key_ref=str(cloud.get("api_key_env") or "OPENAI_API_KEY"),
        connection_id=None,
        binding_source="hybrid_routing.stage_providers",
        params={},
    )


class ModelBindingResolver:
    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root.resolve()

    def resolve(
        self,
        agent_role: str,
        *,
        run_snapshot: dict[str, Any] | None = None,
        session_overrides: dict[str, Any] | None = None,
        user_defaults: dict[str, Any] | None = None,
        workflow_bindings: dict[str, Any] | None = None,
        event_overrides: dict[str, Any] | None = None,
    ) -> ResolvedBinding:
        role = agent_role.strip()
        if not role:
            msg = "agent_role is required"
            raise ValueError(msg)

        if event_overrides and role in event_overrides:
            block = mapping_or_empty(event_overrides[role])
            if block:
                return _binding_from_block(role, block, source="model.binding.overridden")

        if run_snapshot:
            roles = mapping_or_empty(run_snapshot.get("roles"))
            block = mapping_or_empty(roles.get(role))
            if block:
                return _binding_from_block(role, block, source="run.model_bindings_snapshot")

        if session_overrides and role in session_overrides:
            block = mapping_or_empty(session_overrides[role])
            if block:
                return _binding_from_block(role, block, source="session.role_binding_overrides")

        if user_defaults is None:
            from nimbusware_config.model_bindings_store import load_user_defaults

            user_defaults = load_user_defaults(self._repo_root)

        if user_defaults:
            roles = mapping_or_empty(user_defaults.get("roles"))
            block = mapping_or_empty(roles.get(role))
            if block:
                return _binding_from_block(role, block, source="user_defaults")

        if workflow_bindings and role in workflow_bindings:
            block = mapping_or_empty(workflow_bindings[role])
            if block:
                return _binding_from_block(role, block, source="workflow.profile")

        hybrid = _hybrid_routing_binding(self._repo_root, role)
        if hybrid is not None:
            return hybrid

        defaults = _load_defaults_yaml(self._repo_root)
        roles = mapping_or_empty(defaults.get("roles"))
        block = mapping_or_empty(roles.get(role))
        if block:
            return _binding_from_block(role, block, source="configs/model_bindings/defaults.yaml")

        return _global_fallback(self._repo_root, role)

    def chat_json(
        self,
        agent_role: str,
        *,
        messages: list[dict[str, str]],
        timeout_seconds: float = 120.0,
        api_key: str | None = None,
        **resolve_kwargs: Any,
    ) -> dict[str, Any]:
        binding = self.resolve(agent_role, **resolve_kwargs)
        if not binding.model_id:
            msg = f"no model_id resolved for role {agent_role!r}"
            raise ValueError(msg)
        provider = provider_for_preset(
            self._repo_root,
            provider_id=binding.provider_id,
            base_url=binding.base_url,
            api_key=api_key,
        )
        return provider.chat_json(
            model_id=binding.model_id,
            messages=messages,
            timeout_seconds=timeout_seconds,
        )
